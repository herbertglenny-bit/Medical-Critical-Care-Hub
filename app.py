import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import base64
import json
import re
import io
from datetime import datetime
import google.generativeai as genai

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="NanoBanana UCI Station", layout="wide", initial_sidebar_state="expanded")

# --- 2. MOTOR IA (SISTEMA DE TRIAJE AUTOMÁTICO) ---
def get_working_model():
    """Detecta y devuelve el primer modelo funcional disponible"""
    try:
        if "GEMINI_API_KEY" not in st.secrets:
            return None
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Lista de modelos por orden de estabilidad en v1beta
        prioridades = ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-1.5-flash-latest']
        available_models = [m.name for m in genai.list_models()]
        for p in prioridades:
            if p in available_models or f"models/{p}" in available_models:
                return p
        return "gemini-1.5-flash" # Fallback estándar
    except:
        return "gemini-1.5-flash"

ACTIVE_MODEL_NAME = get_working_model()

# --- 3. GESTIÓN DE BASE DE DATOS ---
def get_db_connection():
    return sqlite3.connect('guias_medicas.db', check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS guias 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         titulo TEXT, fecha TEXT, pdf_blob BLOB, 
                         analisis_md TEXT, infografia_html TEXT, mermaid_code TEXT)''')

def guardar_guia(titulo, pdf_bytes, analisis, html, mermaid):
    with get_db_connection() as conn:
        conn.execute('''INSERT INTO guias (titulo, fecha, pdf_blob, analisis_md, infografia_html, mermaid_code) 
                        VALUES (?, ?, ?, ?, ?, ?)''', 
                     (titulo, datetime.now().strftime("%Y-%m-%d"), pdf_bytes, analisis, html, mermaid))

init_db()

# --- 4. FUNCIONES DE LIMPIEZA MÉDICA ---
def clean_ai_output(text, mode="md"):
    if not text: return ""
    text = text.replace("```markdown", "").replace("```html", "").replace("```mermaid", "").replace("```", "")
    if mode == "html":
        match = re.search(r'<div', text)
        if match: text = text[match.start():]
    return text.strip()

# --- 5. TEMPLATE MAESTRO V65 (FULL INTERACTIVE) ---
html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.2.4/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    <script>pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';</script>
    <style>
        :root { --banana: #ffd600; --bg: #0f1113; --card: #ffffff; }
        body, html { margin: 0; padding: 0; height: 100%; font-family: 'Inter', sans-serif; background: var(--bg); overflow: hidden; }
        .main-container { display: flex; width: 100vw; height: 100vh; }
        .pdf-section { width: 50%; height: 100%; display: flex; flex-direction: column; background: #1a1c1e; border-right: 1px solid #333; }
        .pdf-toolbar { height: 50px; background: #000; display: flex; align-items: center; justify-content: center; gap: 20px; color: var(--banana); }
        .pdf-scroll-container { flex: 1; overflow-y: auto; padding: 20px; }
        .pdf-page-canvas { display: block; margin: 0 auto 20px auto; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        .right-panel { width: 50%; height: 100%; display: flex; flex-direction: column; background: #f4f6f8; }
        .tabs-header { height: 60px; background: #fff; display: flex; border-bottom: 2px solid #ddd; }
        .tab-btn { flex: 1; border: none; background: transparent; cursor: pointer; font-weight: 700; font-size: 11px; text-transform: uppercase; }
        .tab-btn.active { border-bottom: 4px solid var(--banana); color: #000; background: #fffbeb; }
        .content-area { flex: 1; overflow-y: auto; position: relative; }
        .tab-content { display: none; padding: 20px; }
        .tab-content.active { display: block; }
        #infografia-visual-container { width: 900px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); overflow: hidden; }
        .poster-header { background: #000; color: var(--banana); padding: 30px; border-bottom: 5px solid var(--banana); }
        #chat-history { height: 400px; overflow-y: auto; background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 10px; }
        .msg { padding: 10px; border-radius: 8px; margin-bottom: 10px; font-size: 14px; }
        .msg.user { background: #eee; text-align: right; }
        .msg.ai { background: #fffbe6; border-left: 4px solid var(--banana); }
        .zoom-btn { cursor: pointer; font-weight: bold; font-size: 20px; background: none; border: none; color: var(--banana); }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button class="zoom-btn" onclick="changeZoom(-0.2)">-</button>
                <span id="zoom-text">100%</span>
                <button class="zoom-btn" onclick="changeZoom(0.2)">+</button>
            </div>
            <div id="pdf-container" class="pdf-scroll-container"></div>
        </div>
        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="showTab('tab-analisis', event)">Análisis</button>
                <button class="tab-btn" onclick="showTab('tab-infografia', event)">Póster</button>
                <button class="tab-btn" onclick="showTab('tab-chat', event)">Chat GPC</button>
            </div>
            <div class="content-area">
                <div id="tab-analisis" class="tab-content active"><div id="m-content"></div></div>
                <div id="tab-infografia" class="tab-content"><div id="infografia-visual-container"></div></div>
                <div id="tab-chat" class="tab-content">
                    <div id="chat-history"></div>
                    <div style="display:flex; gap:10px;">
                        <input type="text" id="c-input" style="flex:1; padding:10px;" placeholder="Pregunta a la guía...">
                        <button onclick="sendMsg()" style="padding:10px; background:#000; color:var(--banana);">ENVIAR</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script>
        const API_KEY = "__API_KEY__"; const MODEL = "__MODEL__";
        const D_PDF = "__PDF_B64__"; 
        let pdfDoc = null, scale = 1.1;

        window.onload = async () => {
            document.getElementById('m-content').innerHTML = marked.parse(__ANALISIS_DATA__);
            document.getElementById('infografia-visual-container').innerHTML = __INFO_DATA__;
            renderPDF(D_PDF);
        };

        async function renderPDF(b64) {
            const task = pdfjsLib.getDocument({data: atob(b64)});
            pdfDoc = await task.promise;
            draw();
        }

        async function draw() {
            const c = document.getElementById('pdf-container'); c.innerHTML = "";
            for(let i=1; i<=pdfDoc.numPages; i++) {
                const p = await pdfDoc.getPage(i);
                const v = p.getViewport({scale});
                const can = document.createElement('canvas');
                can.className = 'pdf-page-canvas';
                can.height = v.height; can.width = v.width;
                c.appendChild(can);
                p.render({canvasContext: can.getContext('2d'), viewport: v});
            }
        }

        function changeZoom(v) { scale += v; draw(); }

        function showTab(id, e) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            e.target.classList.add('active');
        }

        async function sendMsg() {
            const i = document.getElementById('c-input'), h = document.getElementById('chat-history');
            const t = i.value; if(!t) return;
            h.innerHTML += `<div class="msg user">${t}</div>`; i.value = "";
            const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${API_KEY}`, {
                method:'POST', body: JSON.stringify({contents:[{parts:[{text:"Sobre el PDF clínico responde: " + t},{inline_data:{mime_type:"application/pdf", data:D_PDF}}]}]})
            });
            const d = await r.json();
            h.innerHTML += `<div class="msg ai">${marked.parse(d.candidates[0].content.parts[0].text)}</div>`;
            h.scrollTop = h.scrollHeight;
        }
    </script>
</body>
</html>
"""

# --- 6. LÓGICA DE INTERFAZ STREAMLIT ---
with st.sidebar:
    st.title("🍌 NanoBanana UCI")
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    
    with get_db_connection() as conn:
        guias = conn.execute('SELECT id, titulo FROM guias ORDER BY id DESC').fetchall()
    
    for g_id, g_titulo in guias:
        if st.button(f"📄 {g_titulo}", key=f"g_{g_id}", use_container_width=True):
            st.session_state['active_guide_id'] = g_id
            st.rerun()

if modo_admin:
    st.header("Gestión de Evidencia")
    # Copia de seguridad automática
    with get_db_connection() as conn:
        all_data = conn.execute('SELECT * FROM guias').fetchall()
        if all_data:
            st.download_button("📥 Descargar Todas las Guías (Backup)", json.dumps(all_data, default=str), "backup_uci.json")

    file = st.file_uploader("Subir GPC (PDF)", type="pdf")
    if file and st.button("🚀 PROCESAR GUÍA"):
        with st.spinner(f"Analizando con {ACTIVE_MODEL_NAME}..."):
            pdf_bytes = file.read()
            model = genai.GenerativeModel(ACTIVE_MODEL_NAME)
            
            # Análisis 1: Clínico
            p1 = "Rol: Jefe UCI. Analiza Metodología, Análisis Delta (cambios), Bundles y Rincón Residente. En Español."
            res_md = clean_ai_output(model.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p1]).text)
            
            # Análisis 2: Visual
            p2 = "Genera un fragmento DIV HTML con clases poster-header, poster-body, traffic-container (tc-stop, tc-wait, tc-go). Usa iconos emoji."
            res_html = clean_ai_output(model.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p2]).text, "html")
            
            guardar_guia(file.name, pdf_bytes, res_md, res_html, "")
            st.success("✅ Guía integrada correctamente.")
            st.rerun()

# --- 7. RENDERIZADO DEL DASHBOARD ---
if 'active_guide_id' in st.session_state:
    with get_db_connection() as conn:
        guia = conn.execute('SELECT * FROM guias WHERE id = ?', (st.session_state['active_guide_id'],)).fetchone()
    
    if guia:
        pdf_b64 = base64.b64encode(guia[3]).decode('utf-8')
        # Inyección segura de datos
        final_html = html_template.replace("__API_KEY__", st.secrets["GEMINI_API_KEY"])
        final_html = final_html.replace("__MODEL__", ACTIVE_MODEL_NAME)
        final_html = final_html.replace("__PDF_B64__", pdf_b64)
        final_html = final_html.replace("__ANALISIS_DATA__", json.dumps(guia[4]))
        final_html = final_html.replace("__INFO_DATA__", json.dumps(guia[5]))
        
        components.html(final_html, height=1000, scrolling=False)
else:
    st.title("Handover Médico NanoBanana")
    st.markdown("""
    ### Bienvido a la Estación de Trabajo UCI
    Para comenzar, selecciona una de las guías clínicas en el panel lateral. 
    Si es la primera vez, activa el **Modo Administrador** para subir un PDF.
    """)
