import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import base64
import json
import re
import io
from datetime import datetime
import google.generativeai as genai

# --- 1. CONFIGURACIÓN Y ESTÉTICA ---
st.set_page_config(page_title="NanoBanana UCI Station", layout="wide", initial_sidebar_state="expanded")

# --- 2. MOTOR IA (CONFIGURACIÓN ROBUSTA) ---
def get_ia_engine():
    try:
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("⚠️ Falta la clave API. Agrégala en los Secrets de Streamlit.")
            st.stop()
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Autoselección del modelo más estable disponible
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        name = next((m for m in models if "flash" in m), "models/gemini-1.5-flash")
        return genai.GenerativeModel(name), name
    except Exception as e:
        st.error(f"Error de conexión con Google: {e}")
        return None, None

model_ia, active_model_name = get_ia_engine()

# --- 3. GESTIÓN DE DATOS (SQLite + Backup) ---
def get_db():
    conn = sqlite3.connect('guias_medicas.db', check_same_thread=False)
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS guias 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, fecha TEXT, 
                         pdf_blob BLOB, analisis_md TEXT, infografia_html TEXT)''')

init_db()

# --- 4. PLANTILLA HTML DE ALTA FIDELIDAD (V66) ---
# Esta versión incluye scrolls independientes, zoom corregido y soporte de impresión.
html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    <script>pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';</script>
    <style>
        :root { --banana: #ffd600; --bg: #ffffff; }
        body, html { margin:0; padding:0; height:100vh; font-family:'Inter', sans-serif; background:var(--bg); overflow:hidden; }
        .main-container { display:flex; height:100vh; width:100vw; }
        
        /* PANEL PDF: FIJO A LA IZQUIERDA */
        .pdf-panel { width:50%; height:100%; display:flex; flex-direction:column; background:#323639; border-right:2px solid #000; }
        .toolbar { height:50px; background:#202124; display:flex; align-items:center; justify-content:center; gap:15px; color:white; }
        .viewport { flex:1; overflow:auto; padding:20px; display:flex; flex-direction:column; align-items:center; }
        canvas { box-shadow:0 10px 30px rgba(0,0,0,0.5); margin-bottom:20px; background:white; }

        /* PANEL DERECHO: TABS CON SCROLL INDEPENDIENTE */
        .data-panel { width:50%; height:100%; display:flex; flex-direction:column; background:white; }
        .tabs { display:flex; background:#f1f3f4; border-bottom:1px solid #ddd; }
        .tab-btn { flex:1; padding:15px; border:none; cursor:pointer; font-weight:bold; font-size:12px; text-transform:uppercase; color:#5f6368; }
        .tab-btn.active { background:white; color:black; border-bottom:4px solid var(--banana); }
        
        .tab-content { display:none; flex:1; overflow-y:auto; padding:30px; box-sizing:border-box; }
        .tab-content.active { display:block; }
        
        /* ESTILOS DE CONTENIDO */
        .analysis-text { line-height:1.6; color:#202124; font-size:15px; }
        .infography-container { width:100%; overflow-x:auto; }
        
        /* CHATBOT */
        .chat-box { height:80%; display:flex; flex-direction:column; gap:10px; }
        #messages { flex:1; overflow-y:auto; border:1px solid #eee; padding:15px; border-radius:8px; background:#f8f9fa; }
        .chat-input { display:flex; gap:10px; margin-top:10px; }
        
        @media print { .pdf-panel, .tabs, .toolbar, .chat-input { display:none !important; } .tab-content.active { display:block; position:static; width:100%; height:auto; overflow:visible; } }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="pdf-panel">
            <div class="toolbar">
                <button onclick="zoom(-0.2)" style="cursor:pointer">➖</button>
                <span id="zoom-text">110%</span>
                <button onclick="zoom(0.2)" style="cursor:pointer">➕</button>
                <button onclick="window.print()" style="margin-left:20px; background:var(--banana); border:none; padding:5px 10px; font-weight:bold; cursor:pointer">🖨️ IMPRIMIR PÓSTER</button>
            </div>
            <div id="pdf-viewport" class="viewport"></div>
        </div>
        <div class="data-panel">
            <div class="tabs">
                <button class="tab-btn active" onclick="openTab(event, 'analisis')">Análisis Técnico</button>
                <button class="tab-btn" onclick="openTab(event, 'poster')">Póster UCI</button>
                <button class="tab-btn" onclick="openTab(event, 'chat')">Chat Experto</button>
            </div>
            <div id="analisis" class="tab-content active"><div class="analysis-text" id="md-out"></div></div>
            <div id="poster" class="tab-content"><div class="infography-container" id="html-out"></div></div>
            <div id="chat" class="tab-content">
                <div class="chat-box">
                    <div id="messages"></div>
                    <div class="chat-input">
                        <input type="text" id="c-in" style="flex:1; padding:10px;" placeholder="Duda técnica sobre la guía...">
                        <button onclick="askIA()" style="padding:10px; background:black; color:white; border:none; cursor:pointer">ENVIAR</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_KEY = "__API_KEY__";
        const PDF_B64 = "__PDF_B64__";
        const MD_CONTENT = __MD_CONTENT__;
        const HTML_CONTENT = __HTML_CONTENT__;
        
        let pdfDoc = null, currentScale = 1.1;

        window.onload = () => {
            document.getElementById('md-out').innerHTML = marked.parse(MD_CONTENT);
            document.getElementById('html-out').innerHTML = HTML_CONTENT;
            initPDF(PDF_B64);
        };

        async function initPDF(data) {
            const loadingTask = pdfjsLib.getDocument({data: atob(data)});
            pdfDoc = await loadingTask.promise;
            renderPages();
        }

        async function renderPages() {
            const container = document.getElementById('pdf-viewport');
            container.innerHTML = "";
            document.getElementById('zoom-text').innerText = Math.round(currentScale * 100) + "%";
            for (let i = 1; i <= pdfDoc.numPages; i++) {
                const page = await pdfDoc.getPage(i);
                const viewport = page.getViewport({scale: currentScale});
                const canvas = document.createElement('canvas');
                canvas.height = viewport.height; canvas.width = viewport.width;
                container.appendChild(canvas);
                await page.render({canvasContext: canvas.getContext('2d'), viewport}).promise;
            }
        }

        function zoom(v) { currentScale = Math.max(0.5, currentScale + v); renderPages(); }

        function openTab(evt, name) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(name).classList.add('active');
            evt.currentTarget.classList.add('active');
        }

        async function askIA() {
            const inp = document.getElementById('c-in'), box = document.getElementById('messages');
            const txt = inp.value; if(!txt) return;
            box.innerHTML += `<div><b>Pregunta:</b> ${txt}</div>`; inp.value = "";
            
            try {
                const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${API_KEY}`, {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({contents: [{parts: [{text: "Responde de forma técnica sobre el PDF: " + txt}, {inline_data: {mime_type: "application/pdf", data: PDF_B64}}]}]})
                });
                const d = await r.json();
                const res = d.candidates[0].content.parts[0].text;
                box.innerHTML += `<div style="color:#d4a017; margin-bottom:15px;"><b>IA:</b> ${marked.parse(res)}</div>`;
                box.scrollTop = box.scrollHeight;
            } catch(e) { box.innerHTML += "<div>Error de conexión.</div>"; }
        }
    </script>
</body>
</html>
"""

# --- 5. LÓGICA DE NEGOCIO (STREAMLIT) ---
with st.sidebar:
    st.title("🍌 NanoBanana UCI")
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    
    with get_db() as conn:
        guias = conn.execute('SELECT id, titulo FROM guias ORDER BY id DESC').fetchall()
    
    for g_id, g_titulo in guias:
        col_t, col_b = st.columns([0.8, 0.2])
        if col_t.button(f"📄 {g_titulo}", key=f"btn_{g_id}", use_container_width=True):
            st.session_state['active_id'] = g_id
            st.rerun()
        if modo_admin and col_b.button("🗑️", key=f"del_{g_id}"):
            with get_db() as conn:
                conn.execute('DELETE FROM guias WHERE id = ?', (g_id,))
            st.rerun()

if modo_admin:
    st.header("⚙️ Gestión de GPC")
    
    # SECCIÓN DE BACKUP (Crucial para no perder tiempo)
    with st.expander("📥 Copia de Seguridad"):
        st.info("Descarga este archivo para respaldar tus guías. Si la web se borra, podrás restaurarlo.")
        with get_db() as conn:
            all_data = conn.execute('SELECT * FROM guias').fetchall()
            if all_data:
                st.download_button("Guardar Backup (.json)", json.dumps(all_data, default=str), "backup_uci.json")
    
    file = st.file_uploader("Subir PDF de Guía Médica", type="pdf")
    if file and st.button("🚀 PROCESAR E INTEGRAR"):
        with st.spinner(f"IA analizando evidencias con {active_model_name}..."):
            pdf_bytes = file.read()
            # Prompt Técnico Maestro
            p1 = """Analiza este PDF en ESPAÑOL. 
            ROL: Especialista en Medicina Intensiva. 
            Estructura: 
            1. RESUMEN EJECUTIVO (Puntos críticos). 
            2. ANÁLISIS DELTA (¿Qué cambia respecto a la evidencia anterior?). 
            3. BEDSIDE GUIDE (Algoritmos y Bundles paso a paso). 
            4. FARMACOLOGÍA (Dosis, ajustes en falla renal/hepática). 
            5. PERLAS PARA RESIDENTES. 
            Sin introducciones ni formalidades."""
            
            p2 = """Genera un fragmento de DIV HTML para un póster médico. 
            Usa tipografía Inter, colores: Blanco, Negro y Amarillo UCI (#ffd600). 
            Incluye un 'Semáforo de Actuación' (Rojo/Amarillo/Verde) con puntos clave."""
            
            res_md = model_ia.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p1]).text
            res_html = model_ia.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p2]).text
            
            with get_db() as conn:
                conn.execute('INSERT INTO guias (titulo, fecha, pdf_blob, analisis_md, infografia_html) VALUES (?,?,?,?,?)',
                             (file.name, datetime.now().strftime("%Y-%m-%d"), pdf_bytes, res_md, res_html))
            st.success("✅ Guía integrada. Desactiva el modo admin para visualizar.")

elif 'active_id' in st.session_state:
    with get_db() as conn:
        guia = conn.execute('SELECT * FROM guias WHERE id = ?', (st.session_state['active_id'],)).fetchone()
    
    if guia:
        pdf_b64 = base64.b64encode(guia[3]).decode('utf-8')
        render = html_template.replace("__API_KEY__", st.secrets["GEMINI_API_KEY"])
        render = render.replace("__PDF_B64__", pdf_b64)
        render = render.replace("__MD_CONTENT__", json.dumps(guia[4]))
        render = render.replace("__HTML_CONTENT__", json.dumps(guia[5]))
        render = render.replace("__MODEL__", active_model_name)
        
        components.html(render, height=1000, scrolling=False)
else:
    st.title("Estación UCI NanoBanana")
    st.info("👈 Selecciona una guía en el menú lateral.")
