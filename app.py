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

# --- 2. MOTOR IA (CONEXIÓN SEGURA) ---
def get_ia_engine():
    try:
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("⚠️ Configura GEMINI_API_KEY en Secrets.")
            st.stop()
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Intentamos obtener el modelo flash de forma directa
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

model_ia = get_ia_engine()

# --- 3. BASE DE DATOS (ESTRUCTURA BÁSICA) ---
def get_db():
    conn = sqlite3.connect('guias_medicas.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    with get_db() as conn:
        # Solo las columnas esenciales para evitar errores de "columna no encontrada"
        conn.execute('''CREATE TABLE IF NOT EXISTS guias 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         titulo TEXT, fecha TEXT, pdf_blob BLOB, 
                         analisis_md TEXT, infografia_html TEXT)''')
init_db()

# --- 4. PLANTILLA HTML V70 (FOCO EN RENDIMIENTO) ---
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
        
        /* VISOR PDF */
        .pdf-side { width:50%; height:100%; display:flex; flex-direction:column; background:#525659; border-right:1px solid #ddd; }
        .toolbar { height:50px; background:var(--dark); display:flex; align-items:center; justify-content:center; gap:20px; color:white; }
        .viewport { flex:1; overflow:auto; padding:20px; display:flex; flex-direction:column; align-items:center; }
        canvas { box-shadow:0 10px 30px rgba(0,0,0,0.5); margin-bottom:20px; background:white; }

        /* PANELES */
        .data-side { width:50%; height:100%; display:flex; flex-direction:column; background:white; }
        .tabs { display:flex; background:#f1f3f4; border-bottom:1px solid #ddd; height:50px; }
        .tab-btn { flex:1; border:none; cursor:pointer; font-weight:bold; font-size:11px; text-transform:uppercase; }
        .tab-btn.active { background:white; color:black; border-bottom:4px solid var(--banana); }
        .tab-content { display:none; flex:1; overflow-y:auto; padding:30px; box-sizing:border-box; background:white; }
        .tab-content.active { display:block; }
        
        #chat-log { height:400px; overflow-y:auto; border:1px solid #eee; padding:15px; background:#f9f9f9; border-radius:8px; margin-bottom:10px; }
        .chat-row { display:flex; gap:10px; }
        .btn { padding:10px 15px; border:none; border-radius:4px; cursor:pointer; font-weight:bold; }
        .btn-zoom { background:#444; color:white; }
        .btn-dl { background:var(--banana); color:black; }
    </style>
</head>
<body>
    <div class="main">
        <div class="pdf-side">
            <div class="toolbar">
                <button class="btn btn-zoom" onclick="zoom(-0.2)">➖</button>
                <span id="z-txt">110%</span>
                <button class="btn btn-zoom" onclick="zoom(0.2)">➕</button>
                <span id="p-txt" style="font-size:12px; margin-left:10px;">Pág: 1 / -</span>
                <button class="btn btn-dl" onclick="download()">📥 DESCARGAR</button>
            </div>
            <div id="pdf-viewport" class="viewport" onscroll="updatePage()"></div>
        </div>
        <div class="data-side">
            <div class="tabs">
                <button class="tab-btn active" onclick="openTab(event, 'analisis')">Análisis</button>
                <button class="tab-btn" onclick="openTab(event, 'poster')">Póster UCI</button>
                <button class="tab-btn" onclick="openTab(event, 'chat')">Chat Experto</button>
            </div>
            <div id="analisis" class="tab-content active">
                <h1 id="title-out" style="font-weight:900; border-bottom:2px solid #eee; padding-bottom:10px;"></h1>
                <div id="md-out" style="line-height:1.6; color:#333;"></div>
            </div>
            <div id="poster" class="tab-content"><div id="html-out"></div></div>
            <div id="chat" class="tab-content">
                <div id="chat-log"></div>
                <div class="chat-row">
                    <input type="text" id="c-in" style="flex:1; padding:12px; border:1px solid #ddd; border-radius:5px;" placeholder="Pregunta técnica...">
                    <button onclick="ask()" style="padding:12px; background:black; color:white; border-radius:5px;">ENVIAR</button>
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
            document.getElementById('title-out').innerText = GUIA.titulo;
            document.getElementById('md-out').innerHTML = marked.parse(GUIA.analisis);
            document.getElementById('html-out').innerHTML = GUIA.infografia;
            initPDF(PDF_B64);
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
                const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${API_KEY}`, {
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

# --- 5. LÓGICA DE CONTROL ---
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
        with st.spinner("Analizando profundidad clínica..."):
            pdf_bytes = file.read()
            # Prompt Técnico Directo
            p_full = """Analiza este PDF en ESPAÑOL. 
            ROL: Intensivista. 
            Analiza: 1. Metodología. 2. Análisis Delta (Cambios). 3. Bedside Guide. 4. Dosificación. 5. Perlas Clínicas. 
            No uses saludos ni introducciones."""
            
            p_html = "Genera un DIV HTML para un póster médico técnico. Blanco/Negro/Amarillo UCI."
            
            try:
                res_ia = model_ia.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p_full]).text
                res_html = model_ia.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p_html]).text
                
                with get_db() as conn:
                    conn.execute('INSERT INTO guias (titulo, fecha, pdf_blob, analisis_md, infografia_html) VALUES (?,?,?,?,?)',
                                 (file.name, datetime.now().strftime("%Y-%m-%d"), pdf_bytes, res_ia, res_html.replace("```html", "").replace("```", "")))
                st.success("✅ Guía guardada.")
                st.rerun()
            except Exception as e:
                st.error(f"Error de IA: {e}")

elif 'active_id' in st.session_state:
    with get_db() as conn:
        g = conn.execute('SELECT * FROM guias WHERE id = ?', (st.session_state['active_id'],)).fetchone()
    
    if g:
        pdf_b64 = base64.b64encode(g['pdf_blob']).decode('utf-8')
        g_json = {"titulo": g['titulo'], "analisis": g['analisis_md'], "infografia": g['infografia_html']}
        
        render = html_template.replace("__API_KEY__", st.secrets["GEMINI_API_KEY"])
        render = render.replace("__PDF_B64__", pdf_b64)
        render = render.replace("__GUIA_JSON__", json.dumps(g_json))
        
        components.html(render, height=1200, scrolling=False)
else:
    st.info("👈 Selecciona una guía técnica del panel lateral.")
