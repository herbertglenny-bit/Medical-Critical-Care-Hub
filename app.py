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
st.set_page_config(page_title="NanoBanana Medical V56", layout="wide", initial_sidebar_state="expanded")

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

# --- LIMPIEZA DE DATOS ---
def clean_analysis_text(text):
    text = text.replace("```markdown", "").replace("```", "")
    lines = text.split('\n')
    cleaned_lines = []
    found_start = False
    for line in lines:
        if line.strip().startswith('#'): found_start = True
        if found_start:
            line = line.replace('\\%', '%').replace('$', '').replace('\\_', '_').replace('\\>', '>').replace('\\pm', '+/-')
            cleaned_lines.append(line)
    return '\n'.join(cleaned_lines).strip()

def clean_html_output(text):
    text = text.replace("```html", "").replace("```", "")
    start_match = re.search(r'<div class="poster-header"', text)
    if start_match: text = text[start_match.start():]
    end_match = text.rfind("</div>")
    if end_match != -1: text = text[:end_match+6]
    return text.strip()

# --- HTML TEMPLATE V56 (VISUAL REDESIGN) ---
html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>NanoBanana Medical Station</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.2.4/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    <script>pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';</script>
    <style>
        * { box-sizing: border-box; }
        body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; font-family: 'Inter', system-ui, sans-serif; background: #121212; }
        .main-container { display: flex; width: 100vw; height: 100vh; }
        
        .pdf-section { width: 50%; height: 100%; display: flex; flex-direction: column; border-right: 1px solid #333; background: #2c2c2c; }
        .pdf-toolbar { height: 50px; background: #1a1a1a; display: flex; align-items: center; justify-content: center; gap: 20px; }
        .pdf-scroll-container { flex: 1; overflow: auto; padding: 30px; text-align: center; }
        .pdf-page-canvas { display: inline-block; box-shadow: 0 10px 30px rgba(0,0,0,0.5); margin-bottom: 20px; background: white; }

        .right-panel { width: 50%; height: 100%; display: flex; flex-direction: column; background: #fdfdfd; }
        .tabs-header { height: 55px; background: #fff; border-bottom: 3px solid #ffd600; display: flex; }
        .tab-btn { flex: 1; border: none; background: transparent; cursor: pointer; font-weight: 800; color: #444; font-size: 11px; text-transform: uppercase; }
        .tab-btn.active { background: #ffd600; color: #000; }
        
        .content-area { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
        .tab-content { display: none; width: 100%; height: 100%; overflow-y: auto; }
        .tab-content.active { display: block; }
        
        /* ANÁLISIS TEXTUAL */
        .markdown-wrapper { padding: 40px; max-width: 800px; margin: auto; background: white; }
        .markdown-body h1 { border-left: 10px solid #ffd600; padding-left: 15px; color: #000; }
        .markdown-body h2 { background: #fff9c4; padding: 5px 10px; color: #000; }
        
        /* PÓSTER VISUAL NANOBANANA V56 */
        #infografia-wrapper { padding: 40px; text-align: center; background: #e0e0e0; }
        #infografia-visual-container { width: 950px; margin: 0 auto; background: white; box-shadow: 0 40px 100px rgba(0,0,0,0.3); text-align: left; display: inline-block; border-radius: 8px; overflow: hidden; }
        
        .poster-header { background: #111; color: #ffd600; padding: 40px; display: flex; justify-content: space-between; align-items: center; border-bottom: 8px solid #ffd600; }
        .poster-title { font-size: 32px; font-weight: 900; text-transform: uppercase; margin: 0; letter-spacing: 1px; }
        .poster-meta {text-align: right; font-size: 12px; color: #ccc; font-weight: 600; }
        
        .poster-body { padding: 30px 40px; }
        .section-title { font-size: 20px; font-weight: 900; color: #111; border-left: 8px solid #ffd600; padding-left: 15px; margin: 30px 0 20px 0; text-transform: uppercase; display: flex; align-items: center; gap: 10px; }
        
        /* SEMÁFORO VISUAL */
        .traffic-container { display: flex; gap: 20px; margin-top: 15px; }
        .traffic-col { flex: 1; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border: 1px solid #eee; }
        .traffic-title { padding: 15px; font-weight: 900; font-size: 16px; color: white; text-align: center; text-transform: uppercase; letter-spacing: 1px; }
        .tc-stop .traffic-title { background: #d32f2f; }
        .tc-wait .traffic-title { background: #f57c00; }
        .tc-go .traffic-title { background: #388e3c; }
        .traffic-col ul { padding: 20px; margin: 0; list-style: none; background: #fafafa; }
        .traffic-col li { margin-bottom: 10px; font-size: 14px; line-height: 1.4; color: #333; display: flex; gap: 8px; }
        
        /* MÉTRICAS VISUALES */
        .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 20px; }
        .metric-card { background: #111; color: #ffd600; padding: 25px; text-align: center; border-radius: 15px; box-shadow: 0 10px 20px rgba(0,0,0,0.2); border: 2px solid #333; }
        .metric-val { display: block; font-size: 32px; font-weight: 900; margin-bottom: 5px; }
        .metric-lbl { font-size: 11px; font-weight: 700; color: #fff; text-transform: uppercase; letter-spacing: 1px; opacity: 0.8; }

        /* ALGORITMO VISUAL */
        .poster-mermaid { margin-top: 30px; background: #f4f4f4; padding: 30px; border-radius: 15px; border: 2px dashed #ccc; text-align: center; }

        /* CHAT */
        #tab-chat { display: none; width: 100%; height: 100%; flex-direction: column; background: #f5f5f5; }
        .chat-input-box { height: 80px; padding: 15px 25px; background: #fff; border-bottom: 1px solid #ddd; display: flex; gap: 10px; align-items: center; }
        #chat-history { flex: 1; overflow-y: auto; padding: 30px; display: flex; flex-direction: column; gap: 20px; }
        .msg { padding: 15px; border-radius: 15px; font-size: 14px; max-width: 85%; }
        .msg.user { background: #000; color: #ffd600; align-self: flex-end; }
        .msg.ai { background: #fff; border: 1px solid #ddd; align-self: flex-start; }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button onclick="ajustarZoom(-0.2)">➖</button>
                <span id="zoom-level" style="color:white; font-size:12px;">100%</span>
                <button onclick="ajustarZoom(0.2)">➕</button>
            </div>
            <div id="pdf-container" class="pdf-scroll-container"></div>
        </div>
        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="abrirPestana('tab-analisis')">Análisis de la guía</button>
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">Póster Visual (UCI)</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">Consultas</button>
                <button id="btn-save-img" style="background:#000;color:#ffd600;padding:5px 15px;margin-left:auto;display:none;font-weight:bold;border-radius:20px;" onclick="descargarPoster()">📸 GUARDAR PÓSTER</button>
            </div>
            <div class="content-area">
                <div id="tab-analisis" class="tab-content active"><div class="markdown-wrapper"><div id="analisis-content" class="markdown-body"></div></div></div>
                <div id="tab-infografia" class="tab-content"><div id="infografia-wrapper"><div id="infografia-visual-container"></div></div></div>
                <div id="tab-chat" class="tab-content">
                    <div class="chat-input-box">
                        <input type="text" id="user-input" placeholder="Pregunta técnica..." style="flex:1; padding:10px; border-radius:20px; border:1px solid #ddd;">
                        <button onclick="enviarMensaje()" style="background:#000; color:#ffd600; padding:10px 20px; border-radius:20px; font-weight:bold;">ENVIAR</button>
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

        const DATA_PDF = __PDF_DATA__; 
        const DATA_ANALISIS = __ANALISIS_DATA__;
        const DATA_INFO = __INFO_DATA__;
        const DATA_MERMAID = __MERMAID_DATA__;

        window.onload = function() {
            if(DATA_PDF) {
                globalPdfBase64 = DATA_PDF;
                cargarPDF(globalPdfBase64);
                if(DATA_ANALISIS) document.getElementById('analisis-content').innerHTML = marked.parse(DATA_ANALISIS);
                if(DATA_INFO) {
                    document.getElementById('infografia-visual-container').innerHTML = DATA_INFO;
                    if(DATA_MERMAID) {
                        setTimeout(() => { 
                            const target = document.getElementById('mermaid-placeholder'); 
                            if(target) { target.innerHTML = `<pre class="mermaid">${DATA_MERMAID}</pre>`; mermaid.run(); } 
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
            pdfDoc = await loadingTask.promise;
            render();
        }

        async function render() {
            const container = document.getElementById('pdf-container'); container.innerHTML = "";
            document.getElementById('zoom-level').innerText = Math.round(scale * 100) + "%";
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
            h.innerHTML += `<div id="${lid}" class="msg ai">...</div>`;
            h.scrollTop = h.scrollHeight;
            
            chatLog.push({role: "user", text: t});
            let ctx = chatLog.map(e => `${e.role}: ${e.text}`).join('\\n');

            async function fetchAI(idx = 0) {
                if(idx >= MODELS.length) return "Error de conexión con IA.";
                try {
                    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${MODELS[idx]}:generateContent?key=${API_KEY}`, {
                        method: 'POST', body: JSON.stringify({ contents: [{ parts: [{ text: "Responde en ESPAÑOL estrictamente según el PDF. " + ctx }, { inline_data: { mime_type: "application/pdf", data: globalPdfBase64 } }] }] })
                    });
                    const d = await r.json();
                    return d.candidates[0].content.parts[0].text;
                } catch(e) { return fetchAI(idx+1); }
            }
            const res = await fetchAI();
            document.getElementById(lid).innerHTML = marked.parse(res);
            h.scrollTop = h.scrollHeight;
        }

        function descargarPoster() {
            html2canvas(document.getElementById('infografia-visual-container'), { scale: 3, useCORS: true }).then(c => {
                const a = document.createElement('a'); a.download = 'Poster_UCI_NanoBanana.png'; a.href = c.toDataURL(); a.click();
            });
        }
    </script>
</body>
</html>
"""

# --- SIDEBAR & ADMIN ---
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
    st.title("Panel Administrativo UCI")
    file = st.file_uploader("Cargar GPC (PDF)", type="pdf")
    if file and st.button("🚀 PROCESAR GUÍA"):
        with st.spinner("Analizando y diseñando póster visual..."):
            pdf_bytes = file.read()
            def gen(p):
                for m in REAL_MODELS_PYTHON:
                    try: return genai.GenerativeModel(m).generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p]).text
                    except: continue
                return ""

            # PROMPT 1: JEFE DE SERVICIO (ESPAÑOL)
            p1 = """
            # ROL: Jefe de Servicio de Medicina Intensiva y Director de Formación.
            # IDIOMA: ESPAÑOL.
            # INSTRUCCIÓN: Empieza directo con #. NADA DE LATEX. Usa texto plano.
            # TAREAS ESTRUCTURADAS:
            1. Resumen Ejecutivo y Rigor (Metodología GRADE/Expertos y Paciente Tipo UCI).
            2. Análisis Delta (Novedades de alto impacto, Des-implementación/Lo que NO hay que hacer, Cambios en Umbrales exactos).
            3. Guía Operativa Bedside (Algoritmo de decisiones y Bundles de medidas).
            4. El Rincón del Residente (Racional Fisiopatológico, Trial Pivot/Estudio Clave, 3 Flashcards de guardia, Mini-caso clínico).
            5. Áreas de Incertidumbre y Juicio Clínico (Zonas grises).
            """
            analisis = clean_analysis_text(gen(p1))
            
            # PROMPT 2: PÓSTER VISUAL A PIE DE CAMA (ESPAÑOL + ICONOS)
            p2 = """
            # ROL: Diseñador de Infografías Médicas para UCI (NanoBanana Style).
            # OBJETIVO: Crear un resumen gráfico visual, atractivo y esquemático para usar a pie de cama.
            # IDIOMA: ESPAÑOL.
            # INSTRUCCIÓN VISUAL CRÍTICA: Usa EMOJIS relevantes como iconos al principio de los puntos clave (ej: ⛔ para stop, ✅ para hacer, 🩺 para diagnóstico, 💊 para fármacos, ⚠️ para precaución).
            # ESTRUCTURA HTML OBLIGATORIA (Solo genera el HTML dentro de estas etiquetas):
            <div class="poster-header">
                <h1 class="poster-title">[TÍTULO VISUAL CORTO]</h1>
                <div class="poster-meta">🏥 [SOCIEDAD] | 📅 [AÑO] | 🎯 [POBLACIÓN]</div>
            </div>
            <div class="poster-body">
                <div class="section-title">🚦 SEMÁFORO DE ACCIÓN (ANÁLISIS DELTA)</div>
                <div class="traffic-container">
                    <div class="traffic-col tc-stop"><div class="traffic-title">⛔ LO QUE DEBES ABANDONAR (STOP)</div><ul><li>[Icono] Punto 1...</li><li>[Icono] Punto 2...</li></ul></div>
                    <div class="traffic-col tc-wait"><div class="traffic-title">⚠️ ZONAS GRISES (PRECAUCIÓN)</div><ul><li>[Icono] Punto 1...</li><li>[Icono] Punto 2...</li></ul></div>
                    <div class="traffic-col tc-go"><div class="traffic-title">✅ ESTÁNDAR DE CUIDADO (GO)</div><ul><li>[Icono] Punto 1...</li><li>[Icono] Punto 2...</li></ul></div>
                </div>

                <div class="section-title">🔢 DATOS CLAVE A PIE DE CAMA (BIG NUMBERS)</div>
                <div class="metrics-grid">
                    <div class="metric-card"><span class="metric-val">[Valor 1]</span><span class="metric-lbl">[Etiqueta Corta]</span></div>
                    <div class="metric-card"><span class="metric-val">[Valor 2]</span><span class="metric-lbl">[Etiqueta Corta]</span></div>
                    <div class="metric-card"><span class="metric-val">[Valor 3]</span><span class="metric-lbl">[Etiqueta Corta]</span></div>
                </div>

                <div class="section-title">🔄 ALGORITMO DE FLUJO CLÍNICO</div>
                <div id="mermaid-placeholder" class="poster-mermaid"></div>

                <div class="section-title">🧠 TAKE HOME MESSAGES (RESUMEN)</div>
                <ul><li>📌 [Mensaje 1]</li><li>📌 [Mensaje 2]</li><li>📌 [Mensaje 3]</li></ul>
            </div>
            """
            html = clean_html_output(gen(p2))
            
            # PROMPT 3: MERMAID (ESPAÑOL)
            p3 = "Genera un diagrama Mermaid 'graph TD' en ESPAÑOL. Resume el flujo clínico principal. REGLA: Todos los textos de los nodos entre comillas dobles. Ej: A[\"💊 Iniciar vasopresor\"] --> B[\"⚠️ Reevaluar TAM\"]. Solo código."
            mermaid = gen(p3).replace("```mermaid", "").replace("```", "").strip()
            
            st.session_state['temp'] = {'titulo': file.name, 'bytes': pdf_bytes, 'analisis': analisis, 'html': html, 'mermaid': mermaid}

    if 'temp' in st.session_state:
        if st.button("💾 GUARDAR SESIÓN"):
            guardar_guia(st.session_state['temp']['titulo'], st.session_state['temp']['bytes'], st.session_state['temp']['analisis'], st.session_state['temp']['html'], st.session_state['temp']['mermaid'])
            del st.session_state['temp']; st.rerun()

else:
    if 'active_guide_id' in st.session_state:
        guia = obtener_guia_por_id(st.session_state['active_guide_id'])
        if guia:
            # PASO DE DATOS BLINDADO CON JSON DUMPS
            pdf_b64 = base64.b64encode(guia[3]).decode('utf-8')
            f_html = html_template.replace("__API_KEY__", API_KEY)
            f_html = f_html.replace("__MODELS_JSON__", json.dumps(REAL_MODELS_JS))
            f_html = f_html.replace("__PDF_DATA__", json.dumps(pdf_b64))
            f_html = f_html.replace("__ANALISIS_DATA__", json.dumps(guia[4]))
            f_html = f_html.replace("__INFO_DATA__", json.dumps(guia[5]))
            f_html = f_html.replace("__MERMAID_DATA__", json.dumps(guia[6]))
            components.html(f_html, height=1200, scrolling=False)
