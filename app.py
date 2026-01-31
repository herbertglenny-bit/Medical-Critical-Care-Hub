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

# --- 2. MOTOR IA (CONEXIÓN FORZADA) ---
# Forzamos el nombre técnico completo que Google exige en muchas regiones
MODEL_NAME = "models/gemini-1.5-flash"

try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model_ia = genai.GenerativeModel(MODEL_NAME)
    else:
        st.error("⚠️ Error: No se encontró la clave GEMINI_API_KEY en los Secrets.")
        st.stop()
except Exception as e:
    st.error(f"Error crítico de inicialización: {e}")
    st.stop()

# --- 3. BASE DE DATOS (ESTABLE) ---
def get_db():
    conn = sqlite3.connect('guias_medicas.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS guias 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         titulo TEXT, fecha TEXT, pdf_blob BLOB, 
                         analisis_md TEXT, infografia_html TEXT)''')
init_db()

# --- 4. PLANTILLA HTML V72 (PANELES INDEPENDIENTES) ---
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
        :root { --banana: #ffd600; --dark: #323639; }
        body, html { margin:0; padding:0; height:100vh; font-family:'Inter', sans-serif; background:#fff; overflow:hidden; }
        .main { display:flex; height:100vh; width:100vw; }
        
        .pdf-side { width:50%; height:100%; display:flex; flex-direction:column; background:#525659; border-right:1px solid #ddd; }
        .toolbar { height:50px; background:var(--dark); display:flex; align-items:center; justify-content:center; gap:20px; color:white; }
        .viewport { flex:1; overflow:auto; padding:20px; display:flex; flex-direction:column; align-items:center; }
        canvas { box-shadow:0 10px 30px rgba(0,0,0,0.5); margin-bottom:20px; background:white; }

        .data-side { width:50%; height:100%; display:flex; flex-direction:column; background:white; }
        .tabs { display:flex; background:#f1f3f4; border-bottom:1px solid #ddd; height:50px; }
        .tab-btn { flex:1; border:none; cursor:pointer; font-weight:bold; font-size:11px; text-transform:uppercase; color:#5f6368; }
        .tab-btn.active { background:white; color:black; border-bottom:4px solid var(--banana); }
        .tab-content { display:none; flex:1; overflow-y:auto; padding:30px; box-sizing:border-box; background:white; }
        .tab-content.active { display:block; }
        
        #chat-log { height:400px; overflow-y:auto; border:1px solid #eee; padding:15px; background:#f9f9f9; border-radius:8px; margin-bottom:10px; }
    </style>
</head>
<body>
    <div class="main">
        <div class="pdf-side">
            <div class="toolbar">
                <button onclick="zoom(-0.2)">➖</button>
                <span id="z-txt">110%</span>
                <button onclick="zoom(0.2)">➕</button>
                <span id="p-txt" style="font-size:12px; margin-left:10px;">Pág: 1 / -</span>
                <button onclick="download()" style="background:var(--banana); border:none; padding:5px; cursor:pointer; font-weight:bold;">📥 DESCARGAR</button>
            </div>
            <div id="pdf-viewport" class="viewport" onscroll="updatePage()"></div>
        </div>
        <div class="data-side">
            <div class="tabs">
                <button class="tab-btn active" onclick="openTab(event, 'analisis')">Análisis Técnico</button>
                <button class="tab-btn" onclick="openTab(event, 'poster')">Póster UCI</button>
                <button class="tab-btn" onclick="openTab(event, 'chat')">Chat Experto</button>
            </div>
            <div id="analisis" class="tab-content active"><h1 id="title-out"></h1><div id="md-out"></div></div>
            <div id="poster" class="tab-content"><div id="html-out"></div></div>
            <div id="chat" class="tab-content">
                <div id="chat-log"></div>
                <div style="display:flex; gap:10px;">
                    <input type="text" id="c-in" style="flex:1; padding:10px;" placeholder="Duda técnica sobre la guía...">
                    <button onclick="ask()" style="padding:10px; background:black; color:white; border-radius:5px;">ENVIAR</button>
                </div>
            </div>
        </div>
    </div>
    <script>
        const API_KEY = "__API_KEY__"; const MODEL = "__MODEL__";
        const PDF_B64 = "__PDF_B64__"; const GUIA = __GUIA_JSON__;
        let pdfDoc = null, scale = 1.1;

        window.onload = () => {
            document.getElementById('title-out').innerText = GUIA.titulo;
            document.getElementById('md-out').innerHTML = marked.parse(GUIA.analisis);
            document.getElementById('html-out').innerHTML = GUIA.infografia;
            if(PDF_B64) initPDF(PDF_B64);
        };

        async function initPDF(data) {
            const loadingTask = pdfjsLib.getDocument({data: atob(data)});
            pdfDoc = await loadingTask.promise;
            document.getElementById('p-txt').innerText = `Pág: 1 / ${pdfDoc.numPages}`;
            draw();
        }

        async function draw() {
            const view = document.getElementById('pdf-viewport'); view.innerHTML = "";
            document.getElementById('z-txt').innerText = Math.round(scale*100) + "%";
            for(let i=1; i<=pdfDoc.numPages; i++) {
                const page = await pdfDoc.getPage(i);
                const vp = page.getViewport({scale});
                const can = document.createElement('canvas');
                can.height = vp.height; can.width = vp.width;
                view.appendChild(can);
                await page.render({canvasContext: can.getContext('2d'), viewport: vp}).promise;
            }
        }

        function zoom(v) { scale = Math.max(0.4, scale + v); draw(); }

        function updatePage() {
            const cans = document.getElementsByTagName('canvas');
            for(let i=0; i<cans.length; i++) {
                if(cans[i].getBoundingClientRect().top >= 0) {
                    document.getElementById('p-txt').innerText = `Pág: ${i+1} / ${pdfDoc.numPages}`;
                    break;
                }
            }
        }

        function download() {
            const a = document.createElement('a'); a.href = "data:application/pdf;base64," + PDF_B64;
            a.download = GUIA.titulo + ".pdf"; a.click();
        }

        function openTab(e, id) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            e.currentTarget.classList.add('active');
        }

        async function ask() {
            const inp = document.getElementById('c-in'), log = document.getElementById('chat-log');
            const txt = inp.value; if(!txt) return;
            log.innerHTML += `<div><b>Médico:</b> ${txt}</div>`; inp.value = "";
            try {
                const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/${MODEL}:generateContent?key=${API_KEY}`, {
                    method:'POST', headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({contents:[{parts:[{text: "Responde de forma técnica sobre el PDF: " + txt},{inline_data:{mime_type:"application/pdf", data:PDF_B64}}]}]})
                });
                const d = await r.json();
                const res = d.candidates[0].content.parts[0].text;
                log.innerHTML += `<div style="color:#2c3e50; border-left:3px solid var(--banana); padding-left:10px; margin-bottom:20px;"><b>IA:</b> ${marked.parse(res)}</div>`;
                log.scrollTop = log.scrollHeight;
            } catch(e) { log.innerHTML += "<div>Error de conexión.</div>"; }
        }
    </script>
</body>
</html>
"""

# --- 5. LÓGICA STREAMLIT ---
with st.sidebar:
    st.title("🍌 NanoBanana UCI")
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    with get_db() as conn:
        guias = conn.execute('SELECT id, titulo FROM guias ORDER BY id DESC').fetchall()
    for g in guias:
        c1, c2 = st.columns([0.8, 0.2])
        if c1.button(f"📄 {g['titulo']}", key=f"v_{g['id']}", use_container_width=True):
            st.session_state['active_id'] = g['id']
            st.rerun()
        if modo_admin and c2.button("🗑️", key=f"d_{g['id']}"):
            with get_db() as conn:
                conn.execute('DELETE FROM guias WHERE id = ?', (g['id'],))
            st.rerun()

if modo_admin:
    st.header("⚙️ Carga de GPC")
    file = st.file_uploader("Subir PDF", type="pdf")
    if file and st.button("🚀 PROCESAR"):
        with st.spinner("Analizando evidencias clínicas..."):
            try:
                pdf_bytes = file.read()
                p_md = "Analiza este PDF clínico en ESPAÑOL. Estructura: 1. Metodología. 2. Análisis Delta. 3. Bedside Guide. 4. Dosificación. 5. Perlas Clínicas. Sin introducciones."
                p_html = "Genera un DIV HTML de póster médico técnico profesional. Blanco/Negro/Amarillo UCI."
                
                res_ia = model_ia.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p_md]).text
                res_html = model_ia.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p_html]).text
                
                with get_db() as conn:
                    conn.execute('INSERT INTO guias (titulo, fecha, pdf_blob, analisis_md, infografia_html) VALUES (?,?,?,?,?)',
                                 (file.name, datetime.now().strftime("%Y-%m-%d"), pdf_bytes, res_ia, res_html.replace("```html", "").replace("```", "")))
                st.success("✅ Guía guardada.")
                st.rerun()
            except Exception as e:
                st.error(f"Error de conexión con Google: {e}. Verifica que tu clave API en Secrets sea correcta.")

elif 'active_id' in st.session_state:
    with get_db() as conn:
        g = conn.execute('SELECT * FROM guias WHERE id = ?', (st.session_state['active_id'],)).fetchone()
    if g:
        pdf_b64 = base64.b64encode(g['pdf_blob']).decode('utf-8')
        g_json = {"titulo": g['titulo'], "analisis": g['analisis_md'], "infografia": g['infografia_html']}
        render = html_template.replace("__API_KEY__", st.secrets["GEMINI_API_KEY"])
        render = render.replace("__MODEL__", MODEL_NAME)
        render = render.replace("__PDF_B64__", pdf_b64)
        render = render.replace("__GUIA_JSON__", json.dumps(g_json))
        components.html(render, height=1200, scrolling=False)
else:
    st.info("👈 Selecciona una guía técnica del panel lateral.")
