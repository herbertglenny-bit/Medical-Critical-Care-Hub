import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import base64
import json
import re
from datetime import datetime
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="NanoBanana UCI Station", layout="wide", initial_sidebar_state="collapsed")

# --- 2. MOTOR IA ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("⚠️ Configura GEMINI_API_KEY en Secrets.")
    st.stop()

def get_engine():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        name = next((m for m in models if "flash" in m), "models/gemini-1.5-flash")
        return genai.GenerativeModel(name), name
    except: return None, "models/gemini-1.5-flash"

model_ia, active_model_name = get_engine()

# --- 3. BASE DE DATOS (CON METADATA CIENTÍFICA) ---
def get_db():
    return sqlite3.connect('guias_medicas.db', check_same_thread=False)

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS guias 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, autor TEXT, 
                         revista TEXT, fecha_pub TEXT, pdf_blob BLOB, 
                         analisis_md TEXT, infografia_html TEXT)''')
init_db()

# --- 4. PLANTILLA V67 (CONTROLES TOTALES Y CHAT REPARADO) ---
html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script>pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';</script>
    <style>
        :root { --banana: #ffd600; --ui-bg: #f8f9fa; }
        body, html { margin:0; padding:0; height:100vh; font-family:'Inter', sans-serif; background:#fff; overflow:hidden; }
        .main-container { display:flex; height:100vh; width:100vw; }
        
        /* PDF PANEL */
        .pdf-panel { width:50%; height:100%; display:flex; flex-direction:column; background:#525659; border-right:1px solid #ddd; }
        .toolbar { height:50px; background:#323639; display:flex; align-items:center; justify-content:center; gap:20px; color:white; }
        .viewport { flex:1; overflow:auto; padding:20px; display:flex; flex-direction:column; align-items:center; scroll-behavior: smooth; }
        canvas { box-shadow:0 0 20px rgba(0,0,0,0.4); margin-bottom:20px; background:white; }

        /* DATA PANEL */
        .data-panel { width:50%; height:100%; display:flex; flex-direction:column; background:white; }
        .tabs { display:flex; background:var(--ui-bg); border-bottom:1px solid #dee2e6; height:50px; }
        .tab-btn { flex:1; border:none; cursor:pointer; font-weight:700; font-size:11px; text-transform:uppercase; color:#666; background:none; }
        .tab-btn.active { background:white; color:black; border-bottom:3px solid var(--banana); }
        
        .tab-content { display:none; flex:1; overflow-y:auto; padding:35px; box-sizing:border-box; background:white; }
        .tab-content.active { display:block; }

        /* METADATA HEADER */
        .meta-header { border-bottom:2px solid #eee; margin-bottom:20px; padding-bottom:10px; }
        .meta-title { font-weight:900; font-size:20px; margin:0; }
        .meta-sub { font-size:12px; color:#666; margin-top:5px; text-transform:uppercase; letter-spacing:1px; }

        /* CHATBOT */
        .chat-container { height:100%; display:flex; flex-direction:column; }
        #chat-log { flex:1; overflow-y:auto; border:1px solid #eee; padding:15px; background:#fdfdfd; border-radius:8px; margin-bottom:15px; font-size:14px; }
        .chat-input-row { display:flex; gap:10px; }
        
        .btn-action { background:#444; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; font-size:12px; font-weight:bold; }
        .btn-download { background:var(--banana); color:black; }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="pdf-panel">
            <div class="toolbar">
                <button class="btn-action" onclick="changeZoom(-0.2)">➖</button>
                <span id="zoom-info" style="font-size:13px; min-width:40px; text-align:center;">110%</span>
                <button class="btn-action" onclick="changeZoom(0.2)">➕</button>
                <span id="page-counter" style="font-size:12px; margin-left:10px; opacity:0.8;">Pág: 1 / -</span>
                <button class="btn-action btn-download" onclick="downloadPDF()">📥 DESCARGAR</button>
            </div>
            <div id="pdf-viewport" class="viewport" onscroll="updatePageCounter()"></div>
        </div>
        <div class="data-panel">
            <div class="tabs">
                <button class="tab-btn active" onclick="switchTab(event, 't-analisis')">Análisis Técnico</button>
                <button class="tab-btn" onclick="switchTab(event, 't-poster')">Póster UCI</button>
                <button class="tab-btn" onclick="switchTab(event, 't-chat')">Chat Experto</button>
            </div>
            <div id="t-analisis" class="tab-content active">
                <div class="meta-header" id="header-out"></div>
                <div id="md-out"></div>
            </div>
            <div id="t-poster" class="tab-content"><div id="html-out"></div></div>
            <div id="t-chat" class="tab-content">
                <div class="chat-container">
                    <div id="chat-log"></div>
                    <div class="chat-input-row">
                        <input type="text" id="chat-in" style="flex:1; padding:12px; border:1px solid #ddd; border-radius:5px;" placeholder="Duda técnica sobre el protocolo...">
                        <button onclick="sendToIA()" style="padding:12px 20px; background:black; color:white; border-radius:5px; border:none; cursor:pointer; font-weight:bold;">PREGUNTAR</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_KEY = "__API_KEY__";
        const PDF_B64 = "__PDF_B64__";
        const GUIA_DATA = __GUIA_JSON__;
        
        let pdfDoc = null, scale = 1.1;

        window.onload = () => {
            const g = GUIA_DATA;
            document.getElementById('header-out').innerHTML = `
                <h1 class="meta-title">${g.titulo}</h1>
                <div class="meta-sub">${g.autor} | ${g.revista} | ${g.fecha_pub}</div>
            `;
            document.getElementById('md-out').innerHTML = marked.parse(g.analisis);
            document.getElementById('html-out').innerHTML = g.infografia;
            renderPDF(PDF_B64);
        };

        async function renderPDF(data) {
            const loadingTask = pdfjsLib.getDocument({data: atob(data)});
            pdfDoc = await loadingTask.promise;
            document.getElementById('page-counter').innerText = `Pág: 1 / ${pdfDoc.numPages}`;
            draw();
        }

        async function draw() {
            const view = document.getElementById('pdf-viewport'); view.innerHTML = "";
            document.getElementById('zoom-info').innerText = Math.round(scale*100) + "%";
            for(let i=1; i<=pdfDoc.numPages; i++) {
                const page = await pdfDoc.getPage(i);
                const vp = page.getViewport({scale});
                const can = document.createElement('canvas');
                can.height = vp.height; can.width = vp.width;
                view.appendChild(can);
                await page.render({canvasContext: can.getContext('2d'), viewport: vp}).promise;
            }
        }

        function changeZoom(v) { scale = Math.max(0.4, scale + v); draw(); }

        function updatePageCounter() {
            const view = document.getElementById('pdf-viewport');
            const canvases = view.getElementsByTagName('canvas');
            for(let i=0; i<canvases.length; i++) {
                const rect = canvases[i].getBoundingClientRect();
                if(rect.top >= 0 && rect.top < window.innerHeight/2) {
                    document.getElementById('page-counter').innerText = `Pág: ${i+1} / ${pdfDoc.numPages}`;
                    break;
                }
            }
        }

        function downloadPDF() {
            const link = document.createElement('a');
            link.href = "data:application/pdf;base64," + PDF_B64;
            link.download = GUIA_DATA.titulo.replace(/\\s+/g, '_') + ".pdf";
            link.click();
        }

        function switchTab(e, id) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            e.currentTarget.classList.add('active');
        }

        async function sendToIA() {
            const inp = document.getElementById('chat-in'), log = document.getElementById('chat-log');
            const prompt = inp.value; if(!prompt) return;
            log.innerHTML += `<div style="margin-bottom:10px;"><b>Médico:</b> ${prompt}</div>`;
            inp.value = "";
            
            try {
                const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${API_KEY}`, {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        contents: [{parts: [
                            {text: "Actúa como experto clínico. Responde en español sobre este PDF: " + prompt},
                            {inline_data: {mime_type: "application/pdf", data: PDF_B64}}
                        ]}]
                    })
                });
                const data = await res.json();
                const text = data.candidates[0].content.parts[0].text;
                log.innerHTML += `<div style="color:#2c3e50; border-left:3px solid var(--banana); padding-left:10px; margin-bottom:20px;"><b>IA:</b> ${marked.parse(text)}</div>`;
                log.scrollTop = log.scrollHeight;
            } catch(e) { log.innerHTML += "<div>Error de conexión con la IA.</div>"; }
        }
    </script>
</body>
</html>
"""

# --- 5. LÓGICA DE CONTROL (STREAMLIT) ---
with st.sidebar:
    st.title("🍌 NanoBanana UCI")
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    with get_db() as conn:
        guias = conn.execute('SELECT id, titulo FROM guias ORDER BY id DESC').fetchall()
    for g_id, g_titulo in guias:
        c1, c2 = st.columns([0.8, 0.2])
        if c1.button(f"📄 {g_titulo}", key=f"v_{g_id}", use_container_width=True):
            st.session_state['active_id'] = g_id
            st.rerun()
        if modo_admin and c2.button("🗑️", key=f"d_{g_id}"):
            with get_db() as conn: conn.execute('DELETE FROM guias WHERE id = ?', (g_id,))
            st.rerun()

if modo_admin:
    st.header("Carga de Nueva GPC")
    file = st.file_uploader("Documento PDF", type="pdf")
    if file and st.button("🚀 INICIAR ANÁLISIS"):
        with st.spinner("Analizando profundidad clínica..."):
            pdf_bytes = file.read()
            # PROMPT DE EXTRACCIÓN Y ANÁLISIS
            p_full = """Analiza este PDF clínico en ESPAÑOL. 
            PRIMERO: Extrae los metadatos en este formato exacto:
            TITULO: (Nombre de la guía)
            AUTOR: (Sociedad o autores principales)
            REVISTA: (Nombre de la publicación)
            FECHA: (Año de publicación)
            
            LUEGO: Genera el análisis técnico:
            1. METODOLOGÍA Y EVIDENCIA.
            2. ANÁLISIS DELTA (¿Qué ha cambiado respecto a guías previas?).
            3. BEDSIDE GUIDE (Protocolos de actuación inmediata).
            4. DOSIFICACIÓN Y AJUSTES.
            5. PUNTOS CLAVE PARA RESIDENTES.
            
            REGLA: No uses saludos ni introducciones informales."""
            
            p_html = "Genera un DIV HTML para un póster médico. Blanco/Negro/Amarillo UCI. Estilo técnico."
            
            res_ia = model_ia.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p_full]).text
            res_html = model_ia.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p_html]).text
            
            # Parsing de metadatos
            try:
                t = re.search(r"TITULO:\s*(.*)", res_ia).group(1)
                a = re.search(r"AUTOR:\s*(.*)", res_ia).group(1)
                r = re.search(r"REVISTA:\s*(.*)", res_ia).group(1)
                f = re.search(r"FECHA:\s*(.*)", res_ia).group(1)
                clean_md = res_ia.split("LUEGO:")[1] if "LUEGO:" in res_ia else res_ia
            except:
                t, a, r, f, clean_md = file.name, "N/A", "N/A", "N/A", res_ia

            with get_db() as conn:
                conn.execute('INSERT INTO guias (titulo, autor, revista, fecha_pub, pdf_blob, analisis_md, infografia_html) VALUES (?,?,?,?,?,?,?)',
                             (t, a, r, f, pdf_bytes, clean_md.strip(), res_html.replace("```html", "").replace("```", "").strip()))
            st.success("✅ Guía integrada correctamente.")
            st.rerun()

elif 'active_id' in st.session_state:
    with get_db() as conn:
        g = conn.execute('SELECT * FROM guias WHERE id = ?', (st.session_state['active_id'],)).fetchone()
    
    if g:
        pdf_b64 = base64.b64encode(g[5]).decode('utf-8')
        g_json = {
            "titulo": g[1], "autor": g[2], "revista": g[3], "fecha_pub": g[4],
            "analisis": g[6], "infografia": g[7]
        }
        
        render = html_template.replace("__API_KEY__", st.secrets["GEMINI_API_KEY"])
        render = render.replace("__PDF_B64__", pdf_b64)
        render = render.replace("__GUIA_JSON__", json.dumps(g_json))
        
        components.html(render, height=1200, scrolling=False)
else:
    st.info("👈 Selecciona una guía técnica para comenzar.")
