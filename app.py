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
        model = genai.GenerativeModel("gemini-1.5-flash")
        return model, "gemini-1.5-flash"
    except: return None, "Error de conexión"

model_ia, active_model_name = get_engine()

# --- 3. BASE DE DATOS (CONFIGURACIÓN POR NOMBRES) ---
def get_db():
    conn = sqlite3.connect('guias_medicas.db', check_same_thread=False)
    # ESTO ES CLAVE: Permite acceder a los datos por nombre, no por número.
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    with get_db() as conn:
        # Añadimos IF NOT EXISTS y manejamos la estructura
        conn.execute('''CREATE TABLE IF NOT EXISTS guias 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         titulo TEXT, autor TEXT, revista TEXT, fecha_pub TEXT, 
                         pdf_blob BLOB, analisis_md TEXT, infografia_html TEXT)''')
init_db()

# --- 4. PLANTILLA V68 (BLINDADA) ---
html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script>pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';</script>
    <style>
        :root { --banana: #ffd600; }
        body, html { margin:0; padding:0; height:100vh; font-family: sans-serif; overflow:hidden; }
        .main { display:flex; height:100vh; }
        .pdf-side { width:50%; background:#525659; display:flex; flex-direction:column; border-right:1px solid #000; }
        .toolbar { height:50px; background:#323639; display:flex; align-items:center; justify-content:center; gap:15px; color:white; }
        .viewport { flex:1; overflow:auto; padding:20px; display:flex; flex-direction:column; align-items:center; }
        canvas { box-shadow:0 0 20px rgba(0,0,0,0.5); margin-bottom:20px; background:white; }
        .data-side { width:50%; display:flex; flex-direction:column; background:white; }
        .tabs { display:flex; background:#f1f3f4; border-bottom:1px solid #ddd; height:50px; }
        .tab-btn { flex:1; border:none; cursor:pointer; font-weight:bold; font-size:11px; }
        .tab-btn.active { background:white; border-bottom:4px solid var(--banana); }
        .content { flex:1; overflow-y:auto; padding:30px; display:none; }
        .content.active { display:block; }
        .meta-header { border-bottom:2px solid #eee; margin-bottom:20px; padding-bottom:10px; }
        #chat-log { height:300px; overflow-y:auto; border:1px solid #eee; padding:10px; background:#fafafa; margin-bottom:10px; }
    </style>
</head>
<body>
    <div class="main">
        <div class="pdf-side">
            <div class="toolbar">
                <button onclick="changeZoom(-0.2)">➖</button>
                <span id="zoom-txt">110%</span>
                <button onclick="changeZoom(0.2)">➕</button>
                <span id="pg-txt">Pág: 1 / -</span>
                <button onclick="downloadPDF()" style="background:var(--banana); border:none; padding:5px; font-weight:bold; cursor:pointer;">📥 DESCARGAR</button>
            </div>
            <div id="pdf-viewport" class="viewport" onscroll="updatePageCounter()"></div>
        </div>
        <div class="data-side">
            <div class="tabs">
                <button class="tab-btn active" onclick="tab(event, 'analisis')">Análisis</button>
                <button class="tab-btn" onclick="tab(event, 'poster')">Póster</button>
                <button class="tab-btn" onclick="tab(event, 'chat')">Chat</button>
            </div>
            <div id="analisis" class="content active">
                <div class="meta-header" id="header-out"></div>
                <div id="md-out"></div>
            </div>
            <div id="poster" class="content"><div id="html-out"></div></div>
            <div id="chat" class="content">
                <div id="chat-log"></div>
                <div style="display:flex; gap:5px;">
                    <input type="text" id="chat-in" style="flex:1; padding:10px;" placeholder="Pregunta algo...">
                    <button onclick="ask()" style="background:black; color:white; padding:10px;">ENVIAR</button>
                </div>
            </div>
        </div>
    </div>
    <script>
        const API_KEY = "__API_KEY__";
        const PDF_B64 = "__PDF_B64__";
        const GUIA = __GUIA_JSON__;
        let pdfDoc = null, scale = 1.1;

        window.onload = () => {
            document.getElementById('header-out').innerHTML = `<h2>${GUIA.titulo}</h2><p>${GUIA.autor} | ${GUIA.revista} | ${GUIA.fecha}</p>`;
            document.getElementById('md-out').innerHTML = marked.parse(GUIA.analisis);
            document.getElementById('html-out').innerHTML = GUIA.infografia;
            renderPDF(PDF_B64);
        };

        async function renderPDF(data) {
            try {
                const loadingTask = pdfjsLib.getDocument({data: atob(data)});
                pdfDoc = await loadingTask.promise;
                document.getElementById('pg-txt').innerText = `Pág: 1 / ${pdfDoc.numPages}`;
                draw();
            } catch(e) { console.error(e); }
        }

        async function draw() {
            const view = document.getElementById('pdf-viewport'); view.innerHTML = "";
            document.getElementById('zoom-txt').innerText = Math.round(scale*100) + "%";
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
            const canvases = document.getElementsByTagName('canvas');
            for(let i=0; i<canvases.length; i++) {
                if(canvases[i].getBoundingClientRect().top >= 0) {
                    document.getElementById('pg-txt').innerText = `Pág: ${i+1} / ${pdfDoc.numPages}`;
                    break;
                }
            }
        }

        function downloadPDF() {
            const a = document.createElement('a');
            a.href = "data:application/pdf;base64," + PDF_B64;
            a.download = GUIA.titulo + ".pdf";
            a.click();
        }

        function tab(e, id) {
            document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            e.currentTarget.classList.add('active');
        }

        async function ask() {
            const inp = document.getElementById('chat-in'), log = document.getElementById('chat-log');
            const txt = inp.value; if(!txt) return;
            log.innerHTML += `<div><b>Médico:</b> ${txt}</div>`; inp.value = "";
            const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${API_KEY}`, {
                method: 'POST', body: JSON.stringify({contents: [{parts: [{text: "Responde breve: " + txt}, {inline_data: {mime_type: "application/pdf", data: PDF_B64}}]}]})
            });
            const d = await res.json();
            log.innerHTML += `<div style="color:blue;"><b>IA:</b> ${marked.parse(d.candidates[0].content.parts[0].text)}</div>`;
            log.scrollTop = log.scrollHeight;
        }
    </script>
</body>
</html>
"""

# --- 5. LÓGICA DE CONTROL ---
with st.sidebar:
    st.title("🍌 NanoBanana UCI")
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    
    conn = get_db()
    guias = conn.execute('SELECT id, titulo FROM guias ORDER BY id DESC').fetchall()
    
    for g in guias:
        c1, c2 = st.columns([0.8, 0.2])
        if c1.button(f"📄 {g['titulo']}", key=f"v_{g['id']}", use_container_width=True):
            st.session_state['active_id'] = g['id']
            st.rerun()
        if modo_admin and c2.button("🗑️", key=f"d_{g['id']}"):
            conn.execute('DELETE FROM guias WHERE id = ?', (g['id'],))
            conn.commit()
            st.rerun()

if modo_admin:
    st.header("Carga Técnica")
    file = st.file_uploader("Subir PDF", type="pdf")
    if file and st.button("🚀 INICIAR"):
        with st.spinner("Analizando..."):
            pdf_bytes = file.read()
            p = "Extrae TITULO, AUTOR, REVISTA, FECHA y luego un ANÁLISIS DELTA técnico en español."
            res = model_ia.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p]).text
            
            # Intento de extracción simple
            try:
                t = re.search(r"TITULO:\s*(.*)", res).group(1)
            except: t = file.name

            with get_db() as conn:
                conn.execute('INSERT INTO guias (titulo, autor, revista, fecha_pub, pdf_blob, analisis_md, infografia_html) VALUES (?,?,?,?,?,?,?)',
                             (t, "Autor N/A", "Revista N/A", "2024", pdf_bytes, res, "<div>Póster</div>"))
                conn.commit()
            st.success("Guardado.")

elif 'active_id' in st.session_state:
    conn = get_db()
    g = conn.execute('SELECT * FROM guias WHERE id = ?', (st.session_state['active_id'],)).fetchone()
    
    if g:
        # AQUÍ ESTÁ EL CAMBIO: Usamos el nombre 'pdf_blob' en lugar de g[5]
        pdf_b64 = base64.b64encode(g['pdf_blob']).decode('utf-8')
        g_json = {
            "titulo": g['titulo'], "autor": g['autor'], "revista": g['revista'], 
            "fecha": g['fecha_pub'], "analisis": g['analisis_md'], "infografia": g['infografia_html']
        }
        
        render = html_template.replace("__API_KEY__", st.secrets["GEMINI_API_KEY"])
        render = render.replace("__PDF_B64__", pdf_b64)
        render = render.replace("__GUIA_JSON__", json.dumps(g_json))
        components.html(render, height=1000, scrolling=False)
