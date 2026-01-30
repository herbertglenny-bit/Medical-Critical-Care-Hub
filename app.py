import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import base64
import json
import re
from datetime import datetime
import google.generativeai as genai
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="NanoBanana UCI Station", layout="wide", initial_sidebar_state="expanded")

# 2. FUNCIONES DE LIMPIEZA Y SEGURIDAD
def clean_analysis_text(text):
    """Elimina preámbulos y limpia símbolos de formato técnico."""
    text = text.replace("```markdown", "").replace("```", "")
    lines = text.split('\n')
    cleaned_lines = []
    found_start = False
    for line in lines:
        if line.strip().startswith('#'): found_start = True
        if found_start:
            # Limpiar caracteres de escape que ensucian valores médicos
            line = line.replace('\\%', '%').replace('$', '').replace('\\_', '_').replace('\\>', '>').replace('\\pm', '+/-').replace('\\text', '')
            cleaned_lines.append(line)
    return '\n'.join(cleaned_lines).strip()

def clean_html_output(text):
    """Aísla el bloque HTML del póster para evitar texto basura."""
    text = text.replace("```html", "").replace("```", "")
    start_match = re.search(r'<div class="poster-header"', text)
    if start_match: text = text[start_match.start():]
    end_match = text.rfind("</div>")
    if end_match != -1: text = text[:end_match+6]
    return text.strip()

def clean_mermaid_code(text):
    """Asegura que el diagrama sea válido para Mermaid."""
    text = text.replace("```mermaid", "").replace("```", "")
    text = re.sub(r'^mermaid\s+', '', text, flags=re.IGNORECASE)
    return text.strip()

# 3. SEGURIDAD Y CONEXIÓN IA
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except (FileNotFoundError, KeyError):
    st.error("⚠️ Error: Falta 'GEMINI_API_KEY' en Secrets.")
    st.stop()

# 4. MOTOR DE SELECCIÓN DE MODELO
def get_valid_models():
    try:
        all_models = list(genai.list_models())
        valid_models = [m.name for m in all_models if 'generateContent' in m.supported_generation_methods]
        priority = sorted(valid_models, key=lambda x: ('flash' not in x, '2.5' not in x, '2.0' not in x))
        return priority if priority else ["models/gemini-1.5-flash"]
    except:
        return ["models/gemini-1.5-flash"]

REAL_MODELS_PYTHON = get_valid_models()
REAL_MODELS_JS = [m.replace("models/", "") for m in REAL_MODELS_PYTHON]

# 5. BASE DE DATOS (SQLITE)
def init_db():
    conn = sqlite3.connect('guias_medicas.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS guias (
        id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, fecha TEXT, pdf_blob BLOB, 
        analisis_md TEXT, infografia_html TEXT, mermaid_code TEXT)''')
    conn.commit()
    conn.close()

def guardar_guia(titulo, pdf_bytes, analisis, info_html, mermaid):
    conn = sqlite3.connect('guias_medicas.db')
    c = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute('INSERT INTO guias (titulo, fecha, pdf_blob, analisis_md, infografia_html, mermaid_code) VALUES (?, ?, ?, ?, ?, ?)', 
              (titulo, fecha, pdf_bytes, analisis, info_html, mermaid))
    conn.commit()
    conn.close()

def obtener_guias():
    conn = sqlite3.connect('guias_medicas.db')
    c = conn.cursor()
    c.execute('SELECT id, titulo, fecha FROM guias ORDER BY id DESC')
    return c.fetchall()

def obtener_guia_por_id(id_guia):
    conn = sqlite3.connect('guias_medicas.db')
    c = conn.cursor()
    c.execute('SELECT * FROM guias WHERE id = ?', (id_guia,))
    return c.fetchone()

def borrar_guia(id_guia):
    conn = sqlite3.connect('guias_medicas.db')
    c = conn.cursor()
    c.execute('DELETE FROM guias WHERE id = ?', (id_guia,))
    conn.commit()
    conn.close()

init_db()

# 6. INTERFAZ VISUAL (DISEÑO UCI)
html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.2.4/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    <script>pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';</script>
    <style>
        * { box-sizing: border-box; }
        body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; font-family: 'Segoe UI', system-ui, sans-serif; background: #000; color: #fff; }
        .main-container { display: flex; width: 100vw; height: 100vh; }
        
        /* IZQUIERDA: PDF */
        .pdf-section { width: 50%; height: 100%; display: flex; flex-direction: column; border-right: 2px solid #333; background: #1a1a1a; }
        .pdf-toolbar { height: 50px; background: #000; display: flex; align-items: center; justify-content: center; gap: 20px; }
        .pdf-scroll-container { flex: 1; overflow: auto; padding: 20px; text-align: center; }
        .pdf-page-canvas { display: inline-block; box-shadow: 0 0 40px rgba(0,0,0,0.7); margin-bottom: 20px; background: white; }

        /* DERECHA: ANALISIS Y POSTER */
        .right-panel { width: 50%; height: 100%; display: flex; flex-direction: column; background: #fdfdfd; color: #000; }
        .tabs-header { height: 55px; background: #fff; border-bottom: 4px solid #ffd600; display: flex; }
        .tab-btn { flex: 1; border: none; background: transparent; cursor: pointer; font-weight: 900; color: #666; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
        .tab-btn.active { background: #ffd600; color: #000; }
        
        .tab-content { display: none; width: 100%; height: 100%; overflow-y: auto; }
        .tab-content.active { display: block; }
        
        .markdown-wrapper { padding: 40px; max-width: 800px; margin: auto; }
        .markdown-body h1 { border-left: 10px solid #ffd600; padding-left: 15px; font-size: 28px; }
        .markdown-body h2 { background: #fff9c4; padding: 8px; border-radius: 4px; font-size: 18px; margin-top: 25px; }

        /* POSTER VISUAL UCI */
        #infografia-wrapper { padding: 30px; background: #ddd; text-align: center; }
        #infografia-visual-container { width: 950px; margin: 0 auto; background: white; box-shadow: 0 40px 80px rgba(0,0,0,0.3); border-radius: 12px; overflow: hidden; text-align: left; display: inline-block; border: 2px solid #000; }
        .poster-header { background: #000; color: #ffd600; padding: 40px; border-bottom: 10px solid #ffd600; }
        .poster-title { font-size: 38px; font-weight: 900; text-transform: uppercase; margin: 0; line-height: 1; }
        .poster-meta { margin-top: 10px; font-size: 14px; color: #fff; font-weight: 700; opacity: 0.7; }
        .poster-body { padding: 35px; }
        .section-title { font-size: 22px; font-weight: 900; background: #000; color: #ffd600; display: inline-block; padding: 5px 20px; margin: 25px 0 15px 0; border-radius: 4px; }
        .traffic-container { display: flex; gap: 15px; }
        .traffic-col { flex: 1; border-radius: 10px; overflow: hidden; border: 2px solid #000; background: #fff; }
        .traffic-title { padding: 10px; font-weight: 900; color: white; text-align: center; font-size: 13px; text-transform: uppercase; }
        .tc-stop .traffic-title { background: #d32f2f; }
        .tc-wait .traffic-title { background: #f57c00; }
        .tc-go .traffic-title { background: #2e7d32; }
        .traffic-col ul { padding: 15px; font-size: 13px; list-style: none; margin: 0; }
        .traffic-col li { margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 4px; }
        .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
        .metric-card { background: #f5f5f5; border: 2px solid #000; padding: 15px 10px; text-align: center; border-radius: 12px; box-shadow: 4px 4px 0px #ffd600; }
        .metric-val { display: block; font-size: 26px; font-weight: 900; }
        .metric-lbl { font-size: 10px; font-weight: 800; color: #444; text-transform: uppercase; }
        .poster-mermaid { margin-top: 20px; background: #fff; border: 1px solid #000; border-radius: 10px; padding: 20px; text-align: center; }

        /* CHAT */
        #tab-chat { display: none; width: 100%; height: 100%; flex-direction: column; background: #f0f2f5; }
        .chat-input-box { height: 80px; padding: 15px 25px; background: #fff; border-bottom: 1px solid #ddd; display: flex; gap: 10px; align-items: center; }
        #chat-history { flex: 1; overflow-y: auto; padding: 25px; display: flex; flex-direction: column; gap: 12px; }
        .msg { padding: 12px 18px; border-radius: 15px; font-size: 14px; max-width: 80%; border: 1px solid #ddd; }
        .msg.user { background: #000; color: #ffd600; align-self: flex-end; }
        .msg.ai { background: #fff; align-self: flex-start; }
        button { cursor: pointer; border: none; font-weight: 900; }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button onclick="ajustarZoom(-0.2)">➖</button>
                <span id="zoom-level">100%</span>
                <button onclick="ajustarZoom(0.2)">➕</button>
            </div>
            <div id="pdf-container" class="pdf-scroll-container"></div>
        </div>
        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="abrirPestana('tab-analisis')">Análisis de la guía</button>
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">Póster Visual UCI</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">Consultas IA</button>
                <button id="btn-save-img" style="background:#000;color:#ffd600;padding:5px 15px;margin-left:auto;display:none;border-radius:20px;" onclick="descargarPoster()">📸 GUARDAR</button>
            </div>
            <div class="content-area">
                <div id="tab-analisis" class="tab-content active"><div class="markdown-wrapper"><div id="analisis-content" class="markdown-body"></div></div></div>
                <div id="tab-infografia" class="tab-content"><div id="infografia-wrapper"><div id="infografia-visual-container"></div></div></div>
                <div id="tab-chat" class="tab-content">
                    <div class="chat-input-box">
                        <input type="text" id="user-input" placeholder="Pregunta técnica sobre el PDF..." style="flex:1; padding:10px; border-radius:20px; border:1px solid #ddd;">
                        <button onclick="enviarMensaje()" style="background:#000; color:#ffd600; padding:10px 20px; border-radius:20px;">ENVIAR</button>
                    </div>
                    <div id="chat-history"></div>
                </div>
            </div>
        </div>
    </div>
    <script>
        const API_KEY = "__API_KEY__"; const MODELS = __MODELS_JSON__; 
        let pdfDoc = null, scale = 1.0, globalPdfBase64 = null, chatLog = [];
        const DATA_PDF = __PDF_DATA__; const DATA_ANALISIS = __ANALISIS_DATA__;
        const DATA_INFO = __INFO_DATA__; const DATA_MERMAID = __MERMAID_DATA__;

        window.onload = function() {
            if(DATA_PDF) {
                globalPdfBase64 = DATA_PDF; cargarPDF(globalPdfBase64);
                if(DATA_ANALISIS) document.getElementById('analisis-content').innerHTML = marked.parse(DATA_ANALISIS);
                if(DATA_INFO) {
                    document.getElementById('infografia-visual-container').innerHTML = DATA_INFO;
                    if(DATA_MERMAID) {
                        setTimeout(() => { 
                            const target = document.getElementById('mermaid-placeholder'); 
                            if(target) { 
                                try {
                                    target.innerHTML = `<pre class="mermaid">${DATA_MERMAID}</pre>`; 
                                    mermaid.initialize({ startOnLoad: false, theme: 'neutral' });
                                    mermaid.run(); 
                                } catch(e) { target.innerHTML = "<p>Cargando algoritmo...</p>"; }
                            } 
                        }, 800);
                        document.getElementById('btn-save-img').style.display = 'block';
                    }
                }
            }
        };

        function abrirPestana(id) {
            document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).style.display = (id === 'tab-chat') ? 'flex' : 'block';
            if(id.includes('analisis')) document.querySelectorAll('.tab-btn')[0].classList.add('active');
            if(id.includes('infografia')) document.querySelectorAll('.tab-btn')[1].classList.add('active');
            if(id.includes('chat')) document.querySelectorAll('.tab-btn')[2].classList.add('active');
        }

        async function cargarPDF(b64) {
            const loadingTask = pdfjsLib.getDocument({data: atob(b64)});
            pdfDoc = await loadingTask.promise; render();
        }

        async function render() {
            const container = document.getElementById('pdf-container'); container.innerHTML = "";
            for (let i = 1; i <= pdfDoc.numPages; i++) {
                const page = await pdfDoc.getPage(i);
                const vp = page.getViewport({ scale: scale });
                const canvas = document.createElement('canvas');
                canvas.className = 'pdf-page-canvas';
                canvas.height = vp.height; canvas.width = vp.width;
                container.appendChild(canvas);
                page.render({ canvasContext: canvas.getContext('2d'), viewport: vp });
            }
        }
        function ajustarZoom(d) { if(pdfDoc) { scale = Math.max(0.2, scale + d); render(); } }

        async function enviarMensaje() {
            const i = document.getElementById('user-input'), h = document.getElementById('chat-history');
            const t = i.value; if(!t) return;
            h.innerHTML += `<div class="msg user">${t}</div>`; i.value=""; 
            const lid = "l"+Date.now();
            h.innerHTML += `<div id="${lid}" class="msg ai">Consultando evidencia...</div>`;
            h.scrollTop = h.scrollHeight;
            chatLog.push({role: "user", text: t});
            let ctx = chatLog.map(e => `${e.role}: ${e.text}`).join('\\n');

            async function fetchAI(idx = 0) {
                if(idx >= MODELS.length) return "Error de conexión.";
                try {
                    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${MODELS[idx]}:generateContent?key=${API_KEY}`, {
                        method: 'POST', body: JSON.stringify({ contents: [{ parts: [{ text: "Responde en ESPAÑOL basado en el PDF. " + ctx }, { inline_data: { mime_type: "application/pdf", data: globalPdfBase64 } }] }] })
                    });
                    const d = await r.json(); return d.candidates[0].content.parts[0].text;
                } catch(e) { return fetchAI(idx+1); }
            }
            const res = await fetchAI();
            document.getElementById(lid).innerHTML = marked.parse(res);
            h.scrollTop = h.scrollHeight;
        }

        function descargarPoster() {
            html2canvas(document.getElementById('infografia-visual-container'), { scale: 3, useCORS: true }).then(c => {
                const a = document.createElement('a'); a.download = 'Handover_NanoBanana.png'; a.href = c.toDataURL(); a.click();
            });
        }
    </script>
</body>
</html>
"""

# 7. LÓGICA DE PROCESAMIENTO
with st.sidebar:
    st.title("🍌 NanoBanana UCI")
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    guias = obtener_guias()
    for g_id, g_titulo, g_fecha in guias:
        if st.button(f"📄 {g_titulo}", key=f"g_{g_id}", use_container_width=True):
            st.session_state['active_guide_id'] = g_id
            st.rerun()
        if modo_admin:
            if st.button("❌", key=f"d_{g_id}"):
                borrar_guia(g_id); st.rerun()

if modo_admin:
    st.title("Administrador de Sesiones")
    file = st.file_uploader("Subir GPC (PDF)", type="pdf")
    if file and st.button("🚀 TRANSFORMAR GUÍA"):
        with st.spinner("Analizando técnicamente la guía..."):
            pdf_bytes = file.read()
            def gen(p):
                for m in REAL_MODELS_PYTHON:
                    try: return genai.GenerativeModel(m).generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p]).text
                    except: continue
                return ""

            # PROMPT 1: JEFE DE SERVICIO
            p1 = """
            # ROL: Jefe de Servicio de Medicina Intensiva y Director de Formación.
            # IDIOMA: ESPAÑOL.
            # INSTRUCCIÓN CRÍTICA: Empieza directo con #. NADA DE LATEX.
            # TAREAS:
            1. Resumen Ejecutivo y Rigor: Metodología y Paciente Tipo UCI.
            2. Análisis Delta: Ruptura con la práctica anterior (Novedades de alto impacto, Des-implementación/Lo que NO hacer, Cambios en Umbrales exactos).
            3. Guía Operativa Bedside (Checklist): Algoritmo de decisiones y Bundles audidatbles.
            4. El Rincón del Residente: Racional fisiopatológico, Trial Pivot (estudio RCT clave), Flashcards de guardia, Mini-caso de 3 líneas.
            5. Áreas de Incertidumbre y Juicio Clínico.
            """
            analisis = clean_analysis_text(gen(p1))
            
            # PROMPT 2: INFOGRAFÍA VISUAL
            p2 = """
            # ROL: Diseñador Visual UCI.
            # IDIOMA: ESPAÑOL.
            # OBJETIVO: Genera SOLO código HTML para un Póster visual atractivo.
            # REGLA: Usa EMOJIS relevantes (⛔, ✅, 💊, 🩺, ⚠️). NADA DE LATEX.
            # ESTRUCTURA HTML:
            - poster-header (poster-title, poster-meta)
            - poster-body (section-title: usa emojis 🚦, 🔢, 🔄, 🧠)
            - traffic-container (tc-stop: Rojo, tc-wait: Amarillo, tc-go: Verde)
            - metrics-grid (metric-card -> metric-val, metric-lbl) -> "The Big Numbers"
            - ALGORITMO: <div id="mermaid-placeholder" class="poster-mermaid"></div>
            - SECCIÓN RESUMEN: Take Home Messages.
            """
            html = clean_html_output(gen(p2))
            
            # PROMPT 3: MERMAID
            p3 = "Genera un diagrama Mermaid 'graph TD' en ESPAÑOL. Resume el algoritmo principal. REGLA: TODOS los nodos entre comillas dobles. Máximo 6 pasos. Solo código."
            mermaid = clean_mermaid_code(gen(p3))
            
            st.session_state['temp'] = {'titulo': file.name, 'bytes': pdf_bytes, 'analisis': analisis, 'html': html, 'mermaid': mermaid}
            st.success("Procesado con éxito.")

    if 'temp' in st.session_state:
        if st.button("💾 GUARDAR"):
            guardar_guia(st.session_state['temp']['titulo'], st.session_state['temp']['bytes'], st.session_state['temp']['analisis'], st.session_state['temp']['html'], st.session_state['temp']['mermaid'])
            del st.session_state['temp']; st.rerun()

else:
    if 'active_guide_id' in st.session_state:
        guia = obtener_guia_por_id(st.session_state['active_guide_id'])
        if guia:
            pdf_b64 = base64.b64encode(guia[3]).decode('utf-8')
            f_html = html_template.replace("__API_KEY__", API_KEY)
            f_html = f_html.replace("__MODELS_JSON__", json.dumps(REAL_MODELS_JS))
            f_html = f_html.replace("__PDF_DATA__", json.dumps(pdf_b64))
            f_html = f_html.replace("__ANALISIS_DATA__", json.dumps(guia[4]))
            f_html = f_html.replace("__INFO_DATA__", json.dumps(guia[5]))
            f_html = f_html.replace("__MERMAID_DATA__", json.dumps(guia[6]))
            components.html(f_html, height=1200, scrolling=False)
