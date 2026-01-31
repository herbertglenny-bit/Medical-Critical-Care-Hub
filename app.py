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
    st.error("⚠️ Configura la API KEY en Secrets.")
    st.stop()

def get_best_model():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return next((m for m in models if "flash" in m), "models/gemini-1.5-flash")
    except: return "models/gemini-1.5-flash"

ACTIVE_MODEL = get_best_model()

# --- 3. BASE DE DATOS ---
def get_db_connection():
    return sqlite3.connect('guias_medicas.db', check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS guias 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, fecha TEXT, 
                         pdf_blob BLOB, analisis_md TEXT, infografia_html TEXT, mermaid_code TEXT)''')
init_db()

# --- 4. LIMPIEZA ---
def clean_ai_output(text, mode="md"):
    text = text.replace("```markdown", "").replace("```html", "").replace("```", "")
    if mode == "html":
        match = re.search(r'<div', text)
        if match: text = text[match.start():]
    return text.strip()

# --- 5. HTML MAESTRO (CON SCROLLS INDEPENDIENTES) ---
html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <link href="[https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap](https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap)" rel="stylesheet">
    <script src="[https://cdn.jsdelivr.net/npm/marked/marked.min.js](https://cdn.jsdelivr.net/npm/marked/marked.min.js)"></script>
    <script src="[https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js](https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js)"></script>
    <script>pdfjsLib.GlobalWorkerOptions.workerSrc = '[https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js](https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js)';</script>
    <style>
        :root { --banana: #ffd600; --bg: #f0f2f6; }
        body, html { margin: 0; padding: 0; height: 100vh; overflow: hidden; font-family: 'Inter', sans-serif; }
        .main-container { display: flex; height: 100vh; width: 100vw; }
        
        /* SECCIÓN PDF */
        .pdf-section { width: 50%; height: 100%; display: flex; flex-direction: column; background: #333; border-right: 2px solid #000; }
        .pdf-toolbar { height: 50px; background: #000; color: white; display: flex; align-items: center; justify-content: center; gap: 15px; }
        .pdf-viewport { flex: 1; overflow: auto; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        canvas { box-shadow: 0 0 20px rgba(0,0,0,0.5); margin-bottom: 20px; }

        /* SECCIÓN PANELES */
        .right-panel { width: 50%; height: 100%; display: flex; flex-direction: column; background: white; }
        .tabs-header { display: flex; background: #eee; border-bottom: 1px solid #ccc; height: 50px; }
        .tab-btn { flex: 1; border: none; cursor: pointer; font-weight: bold; background: #eee; transition: 0.3s; }
        .tab-btn.active { background: white; border-bottom: 4px solid var(--banana); }
        
        .content-container { flex: 1; overflow: hidden; position: relative; }
        .tab-content { position: absolute; top:0; left:0; width: 100%; height: 100%; overflow: auto; display: none; padding: 30px; box-sizing: border-box; background: white; }
        .tab-content.active { display: block; }

        /* CHATBOT */
        #chat-container { display: flex; flex-direction: column; height: 100%; }
        #chat-messages { flex: 1; overflow-y: auto; border: 1px solid #ddd; padding: 15px; border-radius: 8px; background: #fafafa; margin-bottom: 10px; }
        .input-area { display: flex; gap: 10px; }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button onclick="changeZoom(-0.2)">➖</button>
                <span id="zoom-val">100%</span>
                <button onclick="changeZoom(0.2)">➕</button>
                <a id="download-link" style="color:var(--banana); text-decoration:none; margin-left:20px; font-size:12px;">📥 DESCARGAR</a>
            </div>
            <div id="pdf-viewport" class="pdf-viewport"></div>
        </div>
        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="openTab(event, 'tab-analisis')">Análisis GPC</button>
                <button class="tab-btn" onclick="openTab(event, 'tab-infografia')">Póster UCI</button>
                <button class="tab-btn" onclick="openTab(event, 'tab-chat')">Chat Experto</button>
            </div>
            <div class="content-container">
                <div id="tab-analisis" class="tab-content active"></div>
                <div id="tab-infografia" class="tab-content"></div>
                <div id="tab-chat" class="tab-content">
                    <div id="chat-container">
                        <div id="chat-messages"></div>
                        <div class="input-area">
                            <input type="text" id="chat-input" style="flex:1; padding:10px;" placeholder="Consulta técnica...">
                            <button onclick="sendMessage()" style="padding:10px; background:black; color:white;">ENVIAR</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_KEY = "__API_KEY__";
        const PDF_DATA = "__PDF_DATA__";
        let pdfDoc = null, scale = 1.2;

        window.onload = () => {
            document.getElementById('tab-analisis').innerHTML = marked.parse(__MD_CONTENT__);
            document.getElementById('tab-infografia').innerHTML = __HTML_CONTENT__;
            initPDF();
        };

        async function initPDF() {
            const loadingTask = pdfjsLib.getDocument({data: atob(PDF_DATA)});
            pdfDoc = await loadingTask.promise;
            document.getElementById('download-link').href = "data:application/pdf;base64," + PDF_DATA;
            document.getElementById('download-link').download = "guia_medica.pdf";
            renderPages();
        }

        async function renderPages() {
            const container = document.getElementById('pdf-viewport');
            container.innerHTML = "";
            document.getElementById('zoom-val').innerText = Math.round(scale * 100) + "%";
            for (let i = 1; i <= pdfDoc.numPages; i++) {
                const page = await pdfDoc.getPage(i);
                const viewport = page.getViewport({scale});
                const canvas = document.createElement('canvas');
                canvas.height = viewport.height; canvas.width = viewport.width;
                container.appendChild(canvas);
                page.render({canvasContext: canvas.getContext('2d'), viewport});
            }
        }

        function changeZoom(v) { scale = Math.max(0.5, scale + v); renderPages(); }

        function openTab(evt, tabName) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            evt.currentTarget.classList.add('active');
        }

        async function sendMessage() {
            const input = document.getElementById('chat-input');
            const msg = input.value; if(!msg) return;
            const history = document.getElementById('chat-messages');
            history.innerHTML += `<div><b>Tú:</b> ${msg}</div>`;
            input.value = "";
            
            const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${API_KEY}`, {
                method: 'POST',
                body: JSON.stringify({contents: [{parts: [{text: "Responde de forma técnica sobre el PDF: " + msg}, {inline_data: {mime_type: "application/pdf", data: PDF_DATA}}]}]})
            });
            const data = await response.json();
            history.innerHTML += `<div style="color:#2c3e50; margin-top:10px;"><b>IA:</b> ${marked.parse(data.candidates[0].content.parts[0].text)}</div><hr>`;
            history.scrollTop = history.scrollHeight;
        }
    </script>
</body>
</html>
"""

# --- 6. LOGICA STREAMLIT ---
with st.sidebar:
    st.title("🍌 NanoBanana UCI")
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    with get_db_connection() as conn:
        guias = conn.execute('SELECT id, titulo FROM guias ORDER BY id DESC').fetchall()
    for g_id, g_titulo in guias:
        col1, col2 = st.columns([0.8, 0.2])
        if col1.button(f"📄 {g_titulo}", key=f"g_{g_id}", use_container_width=True):
            st.session_state['active_guide_id'] = g_id
            st.rerun()
        if modo_admin and col2.button("🗑️", key=f"del_{g_id}"):
            with get_db_connection() as conn:
                conn.execute('DELETE FROM guias WHERE id = ?', (g_id,))
            st.rerun()

if modo_admin:
    st.header("Carga Técnica de GPC")
    file = st.file_uploader("Subir PDF", type="pdf")
    if file and st.button("🚀 PROCESAR GUÍA"):
        with st.spinner("Analizando con precisión médica..."):
            pdf_bytes = file.read()
            model = genai.GenerativeModel(ACTIVE_MODEL)
            # PROMPT TÉCNICO PROFUNDO
            p1 = """Analiza este PDF clínico en ESPAÑOL. ROL: Intensivista. 
            Estructura: 1. Metodología y Calidad de Evidencia. 
            2. Análisis Delta (Cambios críticos respecto a guías previas). 
            3. Algoritmos y Bundles (Bedside Guide). 
            4. Farmacocinética y Dosificación sugerida. 
            5. Perlas Clínicas para el manejo en UCI. 
            No incluyas saludos, introducciones ni despedidas. Solo contenido técnico."""
            
            res_md = clean_ai_output(model.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p1]).text)
            
            p2 = "Genera un fragmento DIV HTML de póster médico. Colores: Blanco, Negro y Amarillo UCI. Estilo técnico, iconografía médica, sin saludos."
            res_html = clean_ai_output(model.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p2]).text, "html")
            
            with get_db_connection() as conn:
                conn.execute('INSERT INTO guias (titulo, fecha, pdf_blob, analisis_md, infografia_html) VALUES (?,?,?,?,?)',
                             (file.name, datetime.now().strftime("%Y-%m-%d"), pdf_bytes, res_md, res_html))
            st.success("✅ Guía integrada correctamente.")
            st.rerun()

elif 'active_guide_id' in st.session_state:
    with get_db_connection() as conn:
        guia = conn.execute('SELECT * FROM guias WHERE id = ?', (st.session_state['active_guide_id'],)).fetchone()
    if guia:
        pdf_b64 = base64.b64encode(guia[3]).decode('utf-8')
        final_html = html_template.replace("__API_KEY__", st.secrets["GEMINI_API_KEY"])
        final_html = final_html.replace("__PDF_DATA__", pdf_b64)
        final_html = final_html.replace("__MD_CONTENT__", json.dumps(guia[4]))
        final_html = final_html.replace("__HTML_CONTENT__", json.dumps(guia[5]))
        components.html(final_html, height=1200, scrolling=False)
else:
    st.title("Handover Médico NanoBanana")
    st.info("👈 Selecciona una guía técnica en el lateral.")
