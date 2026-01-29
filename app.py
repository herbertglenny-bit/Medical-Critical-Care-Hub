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
st.set_page_config(page_title="NanoBanana Medical V52", layout="wide", initial_sidebar_state="expanded")

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
    # Eliminar preámbulos tipo "Aquí tienes..." o explicaciones
    lines = text.split('\n')
    cleaned_lines = []
    found_start = False
    for line in lines:
        if line.strip().startswith('#'):
            found_start = True
        if found_start:
            # Eliminar basura de LaTeX que ensucia dosis y porcentajes
            line = line.replace('\\%', '%').replace('$', '').replace('\\_', '_').replace('\\>', '>').replace('\\pm', '+/-').replace('\\text', '')
            cleaned_lines.append(line)
    return '\n'.join(cleaned_lines).strip()

def clean_html_output(text):
    text = text.replace("```html", "").replace("```", "")
    start_match = re.search(r'<div class="poster-header"', text)
    if start_match: text = text[start_match.start():]
    end_match = text.rfind("</div>")
    if end_match != -1: text = text[:end_match+6]
    return text.strip()

# --- HTML TEMPLATE ---
html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>NanoBanana Medical Station</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    <script>pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';</script>
    <style>
        * { box-sizing: border-box; }
        body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; font-family: 'Inter', -apple-system, sans-serif; background: #121212; }
        .main-container { display: flex; width: 100vw; height: 100vh; }
        
        .pdf-section { width: 50%; height: 100%; display: flex; flex-direction: column; border-right: 1px solid #333; background: #2c2c2c; }
        .pdf-toolbar { height: 50px; background: #1a1a1a; display: flex; align-items: center; justify-content: center; gap: 20px; flex-shrink: 0; }
        .pdf-scroll-container { flex: 1; overflow: auto; padding: 30px; text-align: center; }
        .pdf-page-canvas { display: inline-block; box-shadow: 0 10px 30px rgba(0,0,0,0.5); margin-bottom: 20px; background: white; }

        .right-panel { width: 50%; height: 100%; display: flex; flex-direction: column; background: #fdfdfd; }
        .tabs-header { height: 55px; background: #fff; border-bottom: 3px solid #ffd600; display: flex; flex-shrink: 0; }
        .tab-btn { flex: 1; border: none; background: transparent; cursor: pointer; font-weight: 800; color: #444; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
        .tab-btn.active { background: #ffd600; color: #000; }
        
        .content-area { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
        .tab-content { display: none; width: 100%; height: 100%; overflow-y: auto; }
        .tab-content.active { display: block; }
        
        .markdown-wrapper { padding: 40px; max-width: 800px; margin: auto; background: white; min-height: 100%; }
        .markdown-body { font-size: 15px; line-height: 1.6; color: #222; }
        .markdown-body h1 { color: #000; border-left: 10px solid #ffd600; padding-left: 15px; margin: 30px 0 20px 0; }
        .markdown-body h2 { color: #000; background: #fff9c4; padding: 5px 10px; margin-top: 30px; font-size: 18px; }
        .markdown-body table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }
        .markdown-body th { background: #000; color: #fff; padding: 10px; border: 1px solid #333; }
        .markdown-body td { padding: 8px; border: 1px solid #ddd; }

        #infografia-wrapper { padding: 40px; text-align: center; background: #eee; }
        #infografia-visual-container { width: 900px; margin: 0 auto; background: white; box-shadow: 0 40px 100px rgba(0,0,0,0.2); text-align: left; display: inline-block; border-radius: 4px; overflow: hidden; }
        .poster-header { background: #000; color: #ffd600; padding: 50px; }
        .poster-title { font-size: 40px; font-weight: 900; margin: 0; text-transform: uppercase; }
        .poster-meta { margin-top: 10px; color: #fff; opacity: 0.6; font-size: 14px; }
        .poster-body { padding: 40px; }
        .section-title { font-size: 20px; font-weight: 900; color: #000; border-bottom: 5px solid #ffd600; display: inline-block; margin: 25px 0 15px 0; text-transform: uppercase; }
        .traffic-container { display: flex; gap: 15px; }
        .traffic-col { flex: 1; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
        .tc-stop { border-top: 8px solid #f44336; background: #fff5f5; }
        .tc-wait { border-top: 8px solid #ff9800; background: #fff9f0; }
        .tc-go { border-top: 8px solid #4caf50; background: #f5fff6; }
        .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 20px; }
        .metric-card { background: #000; color: #ffd600; padding: 15px 5px; text-align: center; border-radius: 8px; }
        .metric-val { display: block; font-size: 28px; font-weight: 900; }
        .metric-lbl { font-size: 9px; font-weight: 700; text-transform: uppercase; color: #fff; }

        #tab-chat { display: none; width: 100%; height: 100%; flex-direction: column; background: #f5f5f5; }
        .chat-input-box { height: 80px; padding: 15px 25px; background: #fff; border-bottom: 1px solid #ddd; display: flex; gap: 10px; align-items: center; flex-shrink: 0; }
        #chat-history { flex: 1; overflow-y: auto; padding: 30px; display: flex; flex-direction: column; gap: 20px; }
        .msg { padding: 15px 20px; border-radius: 15px; font-size: 14px; max-width: 85%; line-height: 1.5; }
        .msg.user { background: #000; color: #ffd600; align-self: flex-end; }
        .msg.ai { background: #fff; border: 1px solid #ddd; align-self: flex-start; }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button style="padding:5px 10px;" onclick="ajustarZoom(-0.2)">➖</button>
                <span id="zoom-level" style="color:white; font-size:12px; font-weight:bold;">100%</span>
                <button style="padding:5px 10px;" onclick="ajustarZoom(0.2)">➕</button>
            </div>
            <div id="pdf-container" class="pdf-scroll-container"></div>
        </div>
        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="abrirPestana('tab-analisis')">Resumen Jefe Servicio</button>
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">Póster Visual</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">Consultas</button>
                <button id="btn-save-img" style="background:#000;color:#ffd600;padding:0 15px;border-radius:50px;margin-left:auto;display:none;font-size:10px;" onclick="descargarPoster()">📸 GUARDAR</button>
            </div>
            <div class="content-area">
                <div id="tab-analisis" class="tab-content active"><div class="markdown-wrapper"><div id="analisis-content" class="markdown-body"></div></div></div>
                <div id="tab-infografia" class="tab-content"><div id="infografia-wrapper"><div id="infografia-visual-container"></div></div></div>
                <div id="tab-chat" class="tab-content">
                    <div class="chat-input-box">
                        <input type="text" id="user-input" placeholder="Pregunta técnica sobre la guía..." style="flex:1; padding:12px; border:1px solid #ddd; border-radius:30px; outline:none; font-size:14px;" onkeypress="if(event.key==='Enter') enviarMensaje()">
                        <button onclick="enviarMensaje()" style="background:#000; color:#ffd600; padding:10px 20px; border-radius:30px; font-weight:bold;">ENVIAR</button>
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
            } else { document.getElementById('analisis-content').innerHTML = "<div style='text-align:center;margin-top:100px;color:#aaa;'>Selecciona una guía en el menú lateral.</div>"; }
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
            h.innerHTML += `<div id="${loadingId}" class="msg ai" style="color:#888; font-style:italic;">Consultando evidencia...</div>`;
            
            chatLog.push({role: "user", text: t});
            let context = chatLog.map(e => `${e.role}: ${e.text}`).join('\\n');

            async function tryFetch(prompt, attempts = 0) {
                if (attempts >= MODELS.length) throw new Error("Agotado");
                const model = MODELS[attempts];
                const finalPrompt = `ERES UN JEFE DE UCI EXPERTO. RESPONDE ESTRICTAMENTE SEGÚN EL PDF. HISTORIAL: ${context}. PREGUNTA: ${prompt}`;
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
            } catch(e) { document.getElementById(loadingId).innerHTML = "Fallo técnico en la conexión."; }
            h.scrollTop = h.scrollHeight;
        }

        function descargarPoster() {
            const el = document.getElementById('infografia-visual-container');
            html2canvas(el, { scale: 3, useCORS: true }).then(canvas => {
                const a = document.createElement('a'); a.download = 'Handover_NanoBanana.png'; a.href = canvas.toDataURL(); a.click();
            });
        }
    </script>
</body>
</html>
"""

# --- SIDEBAR & ADMINISTRACIÓN ---
with st.sidebar:
    st.title("🍌 NanoBanana")
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    guias = obtener_guias()
    if not guias: st.info("Biblioteca vacía.")
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
    st.title("Gestión de Sesiones Clínicas")
    file = st.file_uploader("Subir GPC (PDF)", type="pdf")
    if file and st.button("🚀 TRANSFORMAR GUÍA CON IA"):
        with st.spinner("Procesando análisis técnico..."):
            pdf_bytes = file.read()
            def safe_gen(prompt):
                for m_name in REAL_MODELS_PYTHON:
                    try:
                        model = genai.GenerativeModel(m_name)
                        return model.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, prompt]).text
                    except: continue
                return ""

            # --- PROMPT 1: JEFE DE SERVICIO (TUS INSTRUCCIONES) ---
            p1 = """
            # ROL
            Actúa como un Jefe de Servicio de Medicina Intensiva, experto en MBE y Director de Residentes.
            # INSTRUCCIONES CRÍTICAS
            TIENES PROHIBIDO SALUDAR O HACER INTRODUCCIONES. TU RESPUESTA DEBE EMPEZAR CON EL CARÁCTER #.
            USA TEXTO PLANO. NADA DE LATEX (NO USES $, _, {, }, text).
            # OBJETIVO
            Genera un informe estructurado según estos puntos:
            1. Resumen Ejecutivo y Rigor: Rigor metodológico y Paciente Tipo.
            2. Análisis Delta: Ruptura con la práctica anterior (Novedades, Des-implementación/De-adoption, Cambios en Umbrales exactos).
            3. Guía Operativa Bedside (Checklist): Algoritmo de decisiones y Bundles audidatbles.
            4. El Rincón del Residente: Racional fisiopatológico, Trial Pivot (RCT fundamental), Flashcards de guardia y Mini-caso clínico evaluativo de 3 líneas.
            5. Áreas de Incertidumbre y Juicio Clínico: Zonas grises y perfiles donde desviarse de la guía.
            """
            analisis_raw = safe_gen(p1)
            analisis_txt = clean_analysis_text(analisis_raw)
            
            # --- PROMPT 2: INFOGRAFÍA TÉCNICA (TUS INSTRUCCIONES) ---
            p2 = """
            # ROL
            Experto en Comunicación Científica Visual. Estructura una Infografía Técnica NanoBanana Style.
            # INSTRUCCIONES
            USA TEXTO TELEGRÁFICO. NADA DE LATEX. SOLO HTML PURO.
            # SECCIONES OBLIGATORIAS (Usa estas clases):
            - poster-header (poster-title, poster-meta)
            - poster-body (section-title)
            - traffic-container (tc-stop: Rojo STOP, tc-wait: Amarillo PRECAUCIÓN, tc-go: Verde GO)
            - metrics-grid (metric-card -> metric-val, metric-lbl) -> "The Big Numbers"
            - ALGORITMO: <div id="mermaid-placeholder" class="poster-mermaid"></div>
            - SECCIÓN 5: Resumen Ejecutivo (Take Home Messages).
            """
            info_html = clean_html_output(safe_gen(p2))
            
            # --- PROMPT 3: MERMAID ---
            mermaid_code = safe_gen("Diagrama mermaid graph TD simple (max 6 nodos) del flujo clínico. Solo código.").replace("```mermaid", "").replace("```", "")
            
            st.session_state['temp'] = {'titulo': file.name, 'bytes': pdf_bytes, 'analisis': analisis_txt, 'html': info_html, 'mermaid': mermaid_code}
            st.success("Análisis estructurado completado.")

    if 'temp' in st.session_state:
        titulo = st.text_input("Nombre de la sesión", value=st.session_state['temp']['titulo'])
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
            components.html(final_html, height=1100, scrolling=False)
    else:
        st.title("Handover Médico NanoBanana")
        st.info("👈 Selecciona una guía clínica procesada para visualizar el análisis de alto nivel.")
