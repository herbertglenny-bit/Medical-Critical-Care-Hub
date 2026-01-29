import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import base64
import json
import re
from datetime import datetime
import google.generativeai as genai
import time

# Configuración
st.set_page_config(page_title="NanoBanana Medical V50", layout="wide", initial_sidebar_state="expanded")

# --- SEGURIDAD ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except (FileNotFoundError, KeyError):
    st.error("⚠️ Error: Falta 'GEMINI_API_KEY' en Secrets.")
    st.stop()

# --- SELECCIÓN DE MODELOS ---
def get_valid_models():
    try:
        all_models = list(genai.list_models())
        valid_models = [m.name for m in all_models if 'generateContent' in m.supported_generation_methods]
        priority_models = sorted(valid_models, key=lambda x: ('flash' not in x, '2.5' not in x, '2.0' not in x))
        return priority_models if priority_models else ["models/gemini-1.5-flash"]
    except:
        return ["models/gemini-1.5-flash"]

REAL_MODELS_PYTHON = get_valid_models()
REAL_MODELS_JS = [m.replace("models/", "") for m in REAL_MODELS_PYTHON]

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('guias_medicas.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS guias (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, fecha TEXT, pdf_blob BLOB, analisis_md TEXT, infografia_html TEXT, mermaid_code TEXT)''')
    conn.commit()
    conn.close()

def guardar_guia(titulo, pdf_bytes, analisis, info_html, mermaid):
    conn = sqlite3.connect('guias_medicas.db')
    c = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute('INSERT INTO guias (titulo, fecha, pdf_blob, analisis_md, infografia_html, mermaid_code) VALUES (?, ?, ?, ?, ?, ?)', (titulo, fecha, pdf_bytes, analisis, info_html, mermaid))
    conn.commit()
    conn.close()

def obtener_guias():
    conn = sqlite3.connect('guias_medicas.db')
    c = conn.cursor()
    c.execute('SELECT id, titulo, fecha FROM guias ORDER BY id DESC')
    data = c.fetchall()
    conn.close()
    return data

def obtener_guia_por_id(id_guia):
    conn = sqlite3.connect('guias_medicas.db')
    c = conn.cursor()
    c.execute('SELECT * FROM guias WHERE id = ?', (id_guia,))
    data = c.fetchone()
    conn.close()
    return data

def borrar_guia(id_guia):
    conn = sqlite3.connect('guias_medicas.db')
    c = conn.cursor()
    c.execute('DELETE FROM guias WHERE id = ?', (id_guia,))
    conn.commit()
    conn.close()

init_db()

# --- LIMPIEZA DE DATOS (REFORZADA) ---
def clean_analysis_text(text):
    # 1. Eliminar cualquier línea introductoria común
    lines = text.split('\n')
    cleaned_lines = []
    found_start = False
    for line in lines:
        if line.strip().startswith('#'):
            found_start = True
        if found_start:
            # 2. Limpiar símbolos de LaTeX o signos extraños en valores
            line = line.replace('\\%', '%').replace('$', '').replace('\\_', '_').replace('\\>', '>')
            cleaned_lines.append(line)
    
    result = '\n'.join(cleaned_lines)
    return result.strip()

def clean_html_output(text):
    text = text.replace("```html", "").replace("```", "")
    start_match = re.search(r'<div class="poster-header"', text)
    if start_match:
        text = text[start_match.start():]
    end_match = text.rfind("</div>")
    if end_match != -1:
        text = text[:end_match+6]
    return text.strip()

# --- HTML TEMPLATE (V50) ---
html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>NanoBanana Medical V50</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    <script>pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';</script>
    <style>
        * { box-sizing: border-box; }
        body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; font-family: 'Segoe UI', Roboto, sans-serif; background: #202124; }
        .main-container { display: flex; width: 100vw; height: 100vh; }
        
        .pdf-section { width: 50%; height: 100%; display: flex; flex-direction: column; border-right: 1px solid #444; background: #525659; }
        .pdf-toolbar { height: 50px; background: #323639; display: flex; align-items: center; justify-content: center; gap: 15px; flex-shrink: 0; }
        .pdf-scroll-container { flex: 1; overflow: auto; padding: 40px; background: #525659; text-align: center; }
        .pdf-page-canvas { display: inline-block; box-shadow: 0 4px 15px rgba(0,0,0,0.6); margin-bottom: 20px; background: white; }

        .right-panel { width: 50%; height: 100%; display: flex; flex-direction: column; background: #f4f7f6; }
        .tabs-header { height: 50px; background: #fff; border-bottom: 2px solid #ffd600; display: flex; flex-shrink: 0; }
        .tab-btn { flex: 1; border: none; background: transparent; cursor: pointer; font-weight: 700; color: #666; font-size: 13px; text-transform: uppercase; }
        .tab-btn.active { background: #ffd600; color: #000; }
        
        .content-area { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
        .tab-content { display: none; width: 100%; height: 100%; overflow-y: auto; }
        .tab-content.active { display: block; }
        
        /* MARKDOWN */
        .markdown-wrapper { padding: 40px; max-width: 850px; margin: auto; background: white; min-height: 100%; }
        .markdown-body { font-size: 16px; line-height: 1.7; color: #333; }
        .markdown-body h1 { color: #000; border-left: 8px solid #ffd600; padding-left: 15px; margin-bottom: 30px; }
        
        /* INFOGRAFIA */
        #infografia-wrapper { padding: 50px; text-align: center; background: #e0e0e0; }
        #infografia-visual-container { width: 900px; margin: 0 auto; background: white; box-shadow: 0 30px 60px rgba(0,0,0,0.4); text-align: left; display: inline-block; }
        
        /* ESTILOS POSTER */
        .poster-header { background: #000; color: #ffd600; padding: 60px 50px; border-bottom: 10px solid #ffd600; }
        .poster-title { font-size: 42px; font-weight: 900; margin: 0; text-transform: uppercase; }
        .poster-meta { margin-top: 15px; font-size: 14px; color: #fff; font-weight: 400; text-transform: uppercase; letter-spacing: 2px; }
        .poster-body { padding: 50px; }
        .section-title { font-size: 20px; font-weight: 900; color: #000; border-bottom: 4px solid #ffd600; display: inline-block; margin: 30px 0 20px 0; }
        .traffic-container { display: flex; gap: 20px; }
        .traffic-col { flex: 1; padding: 20px; border-radius: 8px; border: 1px solid #ddd; }
        .tc-stop { border-left: 10px solid #d32f2f; background: #fff8f8; }
        .tc-wait { border-left: 10px solid #ffa000; background: #fffdf2; }
        .tc-go { border-left: 10px solid #388e3c; background: #f1f8f1; }
        .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
        .metric-card { background: #f5f5f5; border: 2px solid #000; padding: 20px; text-align: center; border-radius: 8px; }
        .metric-val { display: block; font-size: 36px; font-weight: 900; color: #000; }
        .metric-lbl { font-size: 12px; font-weight: 700; color: #666; text-transform: uppercase; }
        .poster-mermaid { margin-top: 20px; background: #fff; padding: 20px; border: 1px solid #eee; }

        /* CHAT */
        #tab-chat { display: none; width: 100%; height: 100%; flex-direction: column; }
        .chat-input-box { height: 80px; padding: 15px 25px; background: #fff; border-bottom: 1px solid #eee; display: flex; gap: 10px; align-items: center; flex-shrink: 0; }
        #chat-history { flex: 1; overflow-y: auto; padding: 30px; background: #f4f7f6; display: flex; flex-direction: column; gap: 20px; }
        .msg { padding: 15px 20px; border-radius: 12px; font-size: 15px; max-width: 85%; line-height: 1.6; }
        .msg.user { background: #000; color: #ffd600; align-self: flex-end; }
        .msg.ai { background: #fff; color: #333; align-self: flex-start; border: 1px solid #ddd; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }

        button { cursor: pointer; border: none; font-weight: 700; }
        .btn-primary { background: #000; color: #ffd600; padding: 10px 20px; border-radius: 5px; margin-left: auto; display: none; }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button style="padding:5px 15px; border-radius:4px;" onclick="ajustarZoom(-0.2)">➖</button>
                <span id="zoom-level" style="color:white; font-size:12px;">100%</span>
                <button style="padding:5px 15px; border-radius:4px;" onclick="ajustarZoom(0.2)">➕</button>
            </div>
            <div id="pdf-container" class="pdf-scroll-container"></div>
        </div>
        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="abrirPestana('tab-analisis')">Análisis</button>
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">Póster NanoBanana</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">Chat Experto</button>
                <button id="btn-save-img" class="btn-primary" onclick="descargarPoster()">📸 GUARDAR</button>
            </div>
            <div class="content-area">
                <div id="tab-analisis" class="tab-content active"><div class="markdown-wrapper"><div id="analisis-content" class="markdown-body"></div></div></div>
                <div id="tab-infografia" class="tab-content"><div id="infografia-wrapper"><div id="infografia-visual-container"></div></div></div>
                <div id="tab-chat" class="tab-content">
                    <div class="chat-input-box">
                        <input type="text" id="user-input" placeholder="Pregunta algo sobre el PDF..." style="flex:1; padding:12px; border:1px solid #ddd; border-radius:5px; outline:none;" onkeypress="if(event.key==='Enter') enviarMensaje()">
                        <button onclick="enviarMensaje()" style="background:#000; color:#ffd600; padding:12px 20px; border-radius:5px;">ENVIAR</button>
                    </div>
                    <div id="chat-history"></div>
                </div>
            </div>
        </div>
    </div>
    <script>
        const API_KEY = "__API_KEY__"; 
        const MODELS = __MODELS_JSON__; 
        let pdfDoc = null, scale = 1.0, globalPdfBase64 = null;
        let chatLog = [];

        mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' });
        const DATA_PDF = "__PDF_DATA__"; 
        const DATA_ANALISIS = `__ANALISIS_DATA__`;
        const DATA_INFO = `__INFO_DATA__`;
        const DATA_MERMAID = `__MERMAID_DATA__`;

        window.onload = function() {
            if(DATA_PDF && DATA_PDF !== "null") {
                globalPdfBase64 = DATA_PDF;
                cargarPDF(globalPdfBase64);
                if(DATA_ANALISIS && DATA_ANALISIS !== "null") document.getElementById('analisis-content').innerHTML = marked.parse(DATA_ANALISIS);
                if(DATA_INFO && DATA_INFO !== "null") {
                    document.getElementById('infografia-visual-container').innerHTML = DATA_INFO;
                    if(DATA_MERMAID && DATA_MERMAID !== "null") {
                        setTimeout(() => { 
                            const target = document.getElementById('mermaid-placeholder'); 
                            if(target) { target.innerHTML = `<div class="mermaid">${DATA_MERMAID}</div>`; mermaid.run(); } 
                        }, 500);
                        document.getElementById('btn-save-img').style.display = 'block';
                    }
                }
            } else { document.getElementById('analisis-content').innerHTML = "<div style='text-align:center;margin-top:100px;color:#aaa;'>Selecciona una guía.</div>"; }
        };

        function abrirPestana(id) {
            document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            const tab = document.getElementById(id);
            tab.style.display = (id === 'tab-chat') ? 'flex' : 'block';
            if(id.includes('analisis')) document.querySelectorAll('.tab-btn')[0].classList.add('active');
            if(id.includes('infografia')) document.querySelectorAll('.tab-btn')[1].classList.add('active');
            if(id.includes('chat')) document.querySelectorAll('.tab-btn')[2].classList.add('active');
            const btn = document.getElementById('btn-save-img');
            btn.style.display = (id === 'tab-infografia' && document.querySelector('.poster-title')) ? 'block' : 'none';
        }

        async function cargarPDF(base64data) {
            const pdfData = atob(base64data);
            const loadingTask = pdfjsLib.getDocument({data: pdfData});
            pdfDoc = await loadingTask.promise;
            renderizarTodo();
        }

        async function renderizarTodo() {
            const container = document.getElementById('pdf-container'); container.innerHTML = "";
            document.getElementById('zoom-level').innerText = Math.round(scale * 100) + "%";
            for (let num = 1; num <= pdfDoc.numPages; num++) {
                const page = await pdfDoc.getPage(num);
                const viewport = page.getViewport({ scale: scale });
                const canvas = document.createElement('canvas');
                canvas.className = 'pdf-page-canvas';
                canvas.height = viewport.height; canvas.width = viewport.width;
                container.appendChild(canvas);
                page.render({ canvasContext: canvas.getContext('2d'), viewport: viewport });
            }
        }
        function ajustarZoom(d) { if(pdfDoc) { scale = Math.max(0.2, scale + d); renderizarTodo(); } }

        async function enviarMensaje() {
            const i = document.getElementById('user-input'), h = document.getElementById('chat-history');
            const t = i.value; if(!t) return;
            h.innerHTML += `<div class="msg user">${t}</div>`; i.value=""; h.scrollTop = h.scrollHeight;
            const loadingId = "load"+Date.now();
            h.innerHTML += `<div id="${loadingId}" class="msg ai" style="color:#888">Buscando en la guía...</div>`;
            
            chatLog.push({role: "user", text: t});
            let context = chatLog.map(e => `${e.role}: ${e.text}`).join('\\n');

            async function tryFetch(prompt, attempts = 0) {
                if (attempts >= MODELS.length) throw new Error("Agotado");
                const model = MODELS[attempts];
                const finalPrompt = `ERES NANOBANANA AI. RESPONDE ÚNICAMENTE CON DATOS DEL PDF ADJUNTO. HISTORIAL: ${context}. PREGUNTA: ${prompt}`;
                try {
                    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${API_KEY}`, {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ contents: [{ parts: [{ text: finalPrompt }, { inline_data: { mime_type: "application/pdf", data: globalPdfBase64 } }] }] })
                    });
                    const d = await r.json();
                    return d.candidates[0].content.parts[0].text;
                } catch(e) { return await tryFetch(prompt, attempts + 1); }
            }

            try {
                const text = await tryFetch(t);
                document.getElementById(loadingId).remove();
                chatLog.push({role: "assistant", text: text});
                h.innerHTML += `<div class="msg ai">${marked.parse(text)}</div>`;
            } catch(e) { document.getElementById(loadingId).innerHTML = "Error de conexión."; }
            h.scrollTop = h.scrollHeight;
        }

        function descargarPoster() {
            const el = document.getElementById('infografia-visual-container');
            html2canvas(el, { scale: 3, useCORS: true }).then(canvas => {
                const a = document.createElement('a'); a.download = 'Poster_NanoBanana.png'; a.href = canvas.toDataURL(); a.click();
            });
        }
    </script>
</body>
</html>
"""

# --- SIDEBAR & ADMINISTRACIÓN ---
with st.sidebar:
    st.title("🍌 NanoBanana")
    st.caption(f"Librería: {genai.__version__}")
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    guias = obtener_guias()
    if not guias: st.info("Sin archivos.")
    for g_id, g_titulo, g_fecha in guias:
        col1, col2 = st.columns([0.8, 0.2])
        if col1.button(f"📄 {g_titulo}", key=f"btn_{g_id}", use_container_width=True):
            st.session_state['active_guide_id'] = g_id
            st.rerun()
        if modo_admin:
            if col2.button("❌", key=f"del_{g_id}"):
                borrar_guia(g_id)
                st.rerun()

if modo_admin:
    st.title("Carga de Guías")
    file = st.file_uploader("Subir PDF", type="pdf")
    if file and st.button("🚀 PROCESAR CON NANOBANANA AI"):
        with st.spinner("Analizando sin ruidos..."):
            pdf_bytes = file.read()
            def safe_gen(prompt):
                for m_name in REAL_MODELS_PYTHON:
                    try:
                        model = genai.GenerativeModel(m_name)
                        return model.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, prompt]).text
                    except: continue
                return ""

            # 1. ANÁLISIS (Órdenes estrictas para evitar charla inicial)
            p1 = "ERES UN MOTOR DE DATOS. TIENES PROHIBIDO SALUDAR. EMPIEZA DIRECTO CON #. Extrae: Definiciones, Algoritmo, Dosis. USA TEXTO PLANO, NADA DE LATEX O SÍMBOLOS EXTRAÑOS."
            analisis_raw = safe_gen(p1)
            analisis_txt = clean_analysis_text(analisis_raw)
            
            # 2. POSTER
            p2 = "Genera SOLO HTML (clases: poster-header, poster-title, poster-meta, poster-body, section-title, traffic-container, traffic-col, tc-stop, tc-wait, tc-go, metrics-grid, metric-card, metric-val, metric-lbl). Sin preámbulos."
            info_html = clean_html_output(safe_gen(p2))
            
            # 3. MERMAID
            mermaid_code = safe_gen("Diagrama mermaid graph TD simple. Solo código.").replace("```mermaid", "").replace("```", "")
            
            st.session_state['temp'] = {'titulo': file.name, 'bytes': pdf_bytes, 'analisis': analisis_txt, 'html': info_html, 'mermaid': mermaid_code}
            st.success("¡Analizado!")

    if 'temp' in st.session_state:
        st.divider()
        titulo = st.text_input("Nombre de la guía", value=st.session_state['temp']['titulo'])
        if st.button("💾 GUARDAR EN BIBLIOTECA"):
            guardar_guia(titulo, st.session_state['temp']['bytes'], st.session_state['temp']['analisis'], st.session_state['temp']['html'], st.session_state['temp']['mermaid'])
            del st.session_state['temp']
            st.rerun()

else:
    if 'active_guide_id' in st.session_state:
        guia = obtener_guia_por_id(st.session_state['active_guide_id'])
        if guia:
            g_pdf = base64.b64encode(guia[3]).decode('utf-8')
            g_analisis = guia[4].replace("`", "\`").replace("${", "\${")
            g_html = guia[5].replace("`", "\`")
            g_mermaid = guia[6].replace("`", "\`")
            
            final_html = html_template.replace("__API_KEY__", API_KEY)
            final_html = final_html.replace("__MODELS_JSON__", json.dumps(REAL_MODELS_JS))
            final_html = final_html.replace("__PDF_DATA__", g_pdf)
            final_html = final_html.replace("__ANALISIS_DATA__", g_analisis)
            final_html = final_html.replace("__INFO_DATA__", g_html)
            final_html = final_html.replace("__MERMAID_DATA__", g_mermaid)
            components.html(final_html, height=1000, scrolling=False)
    else:
        st.title("NanoBanana Medical")
        st.info("Selecciona una guía en el menú lateral.")
