import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import base64
import json
import re
from datetime import datetime
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="NanoBanana UCI Station", layout="wide")

# --- 2. MOTOR IA (SISTEMA ANTIFALLO) ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("⚠️ Error: Configura la GEMINI_API_KEY en los Secrets.")
    st.stop()

def safe_generate_content(pdf_bytes, prompt):
    """Prueba diferentes nombres de modelo para evitar el error NotFound"""
    model_variants = ["gemini-1.5-flash", "models/gemini-1.5-flash", "gemini-1.5-pro"]
    last_error = None
    
    for model_name in model_variants:
        try:
            model = genai.GenerativeModel(model_name=model_name)
            response = model.generate_content([
                {'mime_type': 'application/pdf', 'data': pdf_bytes},
                prompt
            ])
            return response.text, model_name
        except Exception as e:
            last_error = e
            continue
    
    st.error(f"❌ Error crítico de conexión con Google: {last_error}")
    return None, None

# --- 3. BASE DE DATOS ---
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

# --- 4. LIMPIEZA DE DATOS ---
def clean_analysis_text(text):
    if not text: return ""
    text = text.replace("```markdown", "").replace("```", "")
    lines = text.split('\n')
    cleaned = []
    start = False
    for line in lines:
        if line.strip().startswith('#'): start = True
        if start:
            line = line.replace('\\%', '%').replace('$', '').replace('\\_', '_').replace('\\>', '>')
            cleaned.append(line)
    return '\n'.join(cleaned).strip()

def clean_html_output(text):
    if not text: return ""
    text = text.replace("```html", "").replace("```", "")
    match = re.search(r'<div class="poster-header"', text)
    if match: text = text[match.start():]
    else:
        match_any_div = re.search(r'<div', text)
        if match_any_div: text = text[match_any_div.start():]
    end = text.rfind("</div>")
    return text[:end+6].strip() if end != -1 else text.strip()

# --- 5. TEMPLATE MAESTRO V65 ---
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
        * { box-sizing: border-box; }
        body, html { margin: 0; padding: 0; height: 100%; font-family: 'Inter', sans-serif; background: var(--bg); overflow: hidden; }
        .main-container { display: flex; width: 100vw; height: 100vh; }
        .pdf-section { width: 50%; height: 100%; display: flex; flex-direction: column; background: #1a1c1e; border-right: 1px solid #333; }
        .pdf-toolbar { height: 50px; background: #000; display: flex; align-items: center; justify-content: center; gap: 20px; color: var(--banana); font-weight: bold; }
        .pdf-scroll-container { flex: 1; overflow-y: auto; padding: 20px; text-align: center; }
        .pdf-page-canvas { display: block; margin: 0 auto 20px auto; box-shadow: 0 15px 40px rgba(0,0,0,0.6); }
        .right-panel { width: 50%; height: 100%; display: flex; flex-direction: column; background: #f4f6f8; }
        .tabs-header { height: 60px; background: #fff; display: flex; align-items: stretch; border-bottom: 2px solid #ddd; }
        .tab-btn { flex: 1; border: none; background: transparent; cursor: pointer; font-weight: 700; color: #666; font-size: 11px; text-transform: uppercase; transition: 0.3s; }
        .tab-btn.active { border-bottom: 4px solid var(--banana); color: #000; background: #fffbeb; }
        .content-area { flex: 1; overflow: hidden; position: relative; }
        .tab-content { display: none; width: 100%; height: 100%; overflow-y: auto; padding-bottom: 50px; }
        .tab-content.active { display: block; }
        #infografia-wrapper { padding: 40px; text-align: center; background: #e2e8f0; }
        #infografia-visual-container { width: 920px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 50px 100px rgba(0,0,0,0.15); text-align: left; border: 1px solid #ddd; }
        .poster-header { background: #000; color: var(--banana); padding: 40px; border-bottom: 8px solid var(--banana); }
        .poster-title { font-size: 36px; font-weight: 900; margin: 0; line-height: 1.1; }
        .poster-meta { margin-top: 10px; font-size: 13px; color: #fff; opacity: 0.6; text-transform: uppercase; letter-spacing: 1px; }
        .poster-body { padding: 40px; }
        .section-title { font-size: 18px; font-weight: 900; color: #000; margin: 30px 0 15px 0; border-left: 5px solid var(--banana); padding-left: 15px; display: flex; align-items: center; gap: 8px; text-transform: uppercase; }
        .traffic-container { display: flex; gap: 15px; }
        .traffic-col { flex: 1; border-radius: 12px; background: #fff; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .traffic-header { padding: 12px; color: #fff; font-weight: 900; text-align: center; font-size: 12px; }
        .tc-stop .traffic-header { background: #ef4444; }
        .tc-wait .traffic-header { background: #f59e0b; }
        .tc-go .traffic-header { background: #10b981; }
        .traffic-col ul { padding: 15px; margin: 0; font-size: 13px; line-height: 1.5; list-style: none; }
        .traffic-col li { margin-bottom: 8px; padding-left: 20px; position: relative; }
        .traffic-col li::before { content: "•"; position: absolute; left: 0; color: var(--banana); font-weight: bold; }
        .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
        .metric-card { background: #111827; color: var(--banana); padding: 20px 10px; text-align: center; border-radius: 12px; }
        .metric-val { display: block; font-size: 24px; font-weight: 900; color: #fff; }
        .metric-lbl { font-size: 10px; color: var(--banana); font-weight: 700; text-transform: uppercase; margin-top: 5px; }
        #tab-chat { flex-direction: column; background: #f8fafc; }
        .chat-input-box { height: 70px; padding: 15px; background: #fff; border-top: 1px solid #ddd; display: flex; gap: 10px; }
        #chat-history { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 10px; }
        .msg { padding: 12px 16px; border-radius: 12px; font-size: 14px; max-width: 80%; }
        .msg.user { background: #000; color: var(--banana); align-self: flex-end; }
        .msg.ai { background: #fff; border: 1px solid #e2e8f0; align-self: flex-start; }
        button.zoom-btn { background: none; border: none; color: var(--banana); cursor: pointer; font-size: 20px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button class="zoom-btn" onclick="changeZoom(-0.2)">remove_circle</button>
                <span id="zoom-text">100%</span>
                <button class="zoom-btn" onclick="changeZoom(0.2)">add_circle</button>
                <span style="margin-left:20px; font-size:12px;">PÁG: <span id="p-num">1</span>/<span id="p-tot">?</span></span>
            </div>
            <div id="pdf-container" class="pdf-scroll-container"></div>
        </div>
        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="showTab('tab-analisis', event)">Análisis de la guía</button>
                <button class="tab-btn" onclick="showTab('tab-infografia', event)">Póster UCI</button>
                <button class="tab-btn" onclick="showTab('tab-chat', event)">Chat Experto</button>
                <button id="btn-save" style="background:#000;color:var(--banana);margin-left:auto;padding:0 15px;display:none;font-size:10px;" onclick="saveImg()">📸 GUARDAR</button>
            </div>
            <div class="content-area">
                <div id="tab-analisis" class="tab-content active"><div class="markdown-wrapper" id="m-content"></div></div>
                <div id="tab-infografia" class="tab-content"><div id="infografia-wrapper"><div id="infografia-visual-container"></div></div></div>
                <div id="tab-chat" class="tab-content">
                    <div id="chat-history"></div>
                    <div class="chat-input-box">
                        <input type="text" id="c-input" style="flex:1; border-radius:10px; border:1px solid #ddd; padding:10px;" placeholder="Duda técnica...">
                        <button onclick="sendMsg()" style="background:#000; color:var(--banana); padding:0 15px; border-radius:10px;">ENVIAR</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script>
        const API_KEY = "__API_KEY__";
        const D_PDF = __PDF_DATA__; const D_MD = __ANALISIS_DATA__;
        const D_HTML = __INFO_DATA__; const D_MM = __MERMAID_DATA__;
        let pdfDoc = null, scale = 1.1, chatLog = [];

        window.onload = () => {
            if(D_PDF) {
                renderPDF(D_PDF);
                document.getElementById('m-content').innerHTML = marked.parse(D_MD);
                document.getElementById('infografia-visual-container').innerHTML = D_HTML;
                document.getElementById('btn-save').style.display = 'block';
            }
            document.getElementById('pdf-container').onscroll = upPage;
        };

        async function renderPDF(b64) {
            const task = pdfjsLib.getDocument({data: atob(b64)});
            pdfDoc = await task.promise;
            document.getElementById('p-tot').innerText = pdfDoc.numPages;
            draw();
        }

        async function draw() {
            const c = document.getElementById('pdf-container'); c.innerHTML = "";
            document.getElementById('zoom-text').innerText = Math.round(scale*100)+"%";
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

        function upPage() {
            const cans = document.getElementsByClassName('pdf-page-canvas');
            for(let i=0; i<cans.length; i++) {
                if(cans[i].getBoundingClientRect().top >= 0) {
                    document.getElementById('p-num').innerText = i+1; break;
                }
            }
        }

        function changeZoom(v) { scale = Math.max(0.4, scale+v); draw(); }

        function showTab(id, event) {
            document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            event.target.classList.add('active');
        }

        async function sendMsg() {
            const i = document.getElementById('c-input'), h = document.getElementById('chat-history');
            const t = i.value; if(!t) return;
            h.innerHTML += `<div class="msg user">${t}</div>`; i.value = "";
            const lid = "l"+Date.now();
            h.innerHTML += `<div id="${lid}" class="msg ai">...</div>`;
            h.scrollTop = h.scrollHeight;
            
            try {
                // Intentar el chat con el modelo flash estándar
                const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${API_KEY}`, {
                    method:'POST', body: JSON.stringify({contents:[{parts:[{text:"Responde en ESPAÑOL basado en el PDF: " + t},{inline_data:{mime_type:"application/pdf", data:D_PDF}}]}]})
                });
                const d = await r.json();
                const res = d.candidates[0].content.parts[0].text;
                document.getElementById(lid).innerHTML = marked.parse(res);
            } catch(e) {
                document.getElementById(lid).innerHTML = "Error al conectar con la IA.";
            }
            h.scrollTop = h.scrollHeight;
        }

        function saveImg() {
            html2canvas(document.getElementById('infografia-visual-container'), {scale:3}).then(c => {
                const a = document.createElement('a'); a.download = 'Poster_UCI.png'; a.href = c.toDataURL(); a.click();
            });
        }
    </script>
</body>
</html>
"""

# --- 6. LÓGICA DE STREAMLIT ---
with st.sidebar:
    st.title("🍌 NanoBanana UCI")
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    
    with get_db_connection() as conn:
        guias = conn.execute('SELECT id, titulo, fecha FROM guias ORDER BY id DESC').fetchall()
    
    for g_id, g_titulo, g_fecha in guias:
        col_t, col_d = st.columns([0.8, 0.2])
        with col_t:
            if st.button(f"📄 {g_titulo}", key=f"g_{g_id}", use_container_width=True):
                st.session_state['active_guide_id'] = g_id
                st.rerun()
        with col_d:
            if modo_admin:
                if st.button("🗑️", key=f"del_{g_id}"):
                    with get_db_connection() as conn:
                        conn.execute('DELETE FROM guias WHERE id = ?', (g_id,))
                    st.rerun()

if modo_admin:
    st.title("Admin: Carga de GPC")
    
    with st.expander("📥 Copia de Seguridad"):
        with get_db_connection() as conn:
            all_data = conn.execute('SELECT * FROM guias').fetchall()
            if all_data:
                st.download_button("Descargar Backup (.json)", json.dumps(all_data, default=str), "backup_uci.json")

    file = st.file_uploader("Subir PDF", type="pdf")
    
    if file and st.button("🚀 PROCESAR"):
        with st.spinner("Analizando evidencias clínicas..."):
            pdf_bytes = file.read()
            
            # PROMPTS
            p1 = "# ROL: Jefe UCI. Analiza Metodología, Análisis Delta, Bundles y Rincón Residente."
            p2 = "# ROL: Diseñador UCI. Genera DIV HTML con poster-header, poster-body, traffic-container, metrics-grid. Emojis."
            p3 = "# Mermaid TD Algoritmo clínico. Solo código."
            
            # EJECUCIÓN CON AUTODETECCIÓN DE MODELO
            raw_analisis, mod_used = safe_generate_content(pdf_bytes, p1)
            if raw_analisis:
                analisis = clean_analysis_text(raw_analisis)
                raw_html, _ = safe_generate_content(pdf_bytes, p2)
                html = clean_html_output(raw_html)
                raw_mermaid, _ = safe_generate_content(pdf_bytes, p3)
                mermaid = raw_mermaid.replace("```mermaid", "").replace("```", "").strip() if raw_mermaid else ""
                
                guardar_guia(file.name, pdf_bytes, analisis, html, mermaid)
                st.success(f"✅ Éxito usando {mod_used}. Guía guardada.")
                st.rerun()

# --- 7. RENDERIZADO ---
if 'active_guide_id' in st.session_state:
    with get_db_connection() as conn:
        guia = conn.execute('SELECT * FROM guias WHERE id = ?', (st.session_state['active_guide_id'],)).fetchone()
    
    if guia:
        pdf_b64 = base64.b64encode(guia[3]).decode('utf-8')
        f_html = html_template.replace("__API_KEY__", API_KEY)
        f_html = f_html.replace("__PDF_DATA__", json.dumps(pdf_b64))
        f_html = f_html.replace("__ANALISIS_DATA__", json.dumps(guia[4]))
        f_html = f_html.replace("__INFO_DATA__", json.dumps(guia[5]))
        f_html = f_html.replace("__MERMAID_DATA__", json.dumps(guia[6]))
        
        components.html(f_html, height=1300, scrolling=False)
else:
    st.info("👈 Selecciona una guía clínica en el lateral.")
