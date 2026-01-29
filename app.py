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
st.set_page_config(page_title="Estación Médica NanoBanana", layout="wide", initial_sidebar_state="expanded")

# --- SEGURIDAD ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except (FileNotFoundError, KeyError):
    st.error("⚠️ Error: Falta 'GEMINI_API_KEY' en Secrets.")
    st.stop()

# --- SELECCIÓN DE MODELOS INTELIGENTE ---
def get_valid_models():
    try:
        all_models = list(genai.list_models())
        valid_models = [m.name for m in all_models if 'generateContent' in m.supported_generation_methods]
        # Prioridad: Flash > Pro > Otros (para velocidad)
        # Buscamos modelos 2.5 o 2.0 primero
        priority_models = sorted(valid_models, key=lambda x: ('flash' not in x, '2.5' not in x, '2.0' not in x))
        if not priority_models: return ["models/gemini-1.5-flash"]
        return priority_models
    except:
        return ["models/gemini-1.5-flash"]

REAL_MODELS_PYTHON = get_valid_models()
# Limpiamos el prefijo 'models/' para que JS lo entienda bien
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

# --- HTML TEMPLATE (V48 - NanoBanana Style) ---
html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>NanoBanana Viewer</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    <script>pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';</script>
    <style>
        * { box-sizing: border-box; }
        body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background: #202124; }
        .main-container { display: flex; width: 100vw; height: 100vh; }
        
        /* IZQUIERDA */
        .pdf-section { width: 50%; min-width: 50%; height: 100%; display: flex; flex-direction: column; border-right: 1px solid #444; background: #525659; }
        .pdf-toolbar { height: 50px; background: #323639; display: flex; align-items: center; justify-content: center; gap: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); z-index: 10; flex-shrink: 0; }
        .pdf-scroll-container { flex: 1; overflow: auto; padding: 40px; background: #525659; text-align: center; display: block; }
        .pdf-page-canvas { display: inline-block; box-shadow: 0 4px 15px rgba(0,0,0,0.6); margin-bottom: 20px; vertical-align: top; background: white; }

        /* DERECHA */
        .right-panel { width: 50%; min-width: 50%; height: 100%; display: flex; flex-direction: column; background: #f9f9f9; }
        .tabs-header { height: 50px; background: #fff; border-bottom: 2px solid #ffca28; display: flex; flex-shrink: 0; z-index: 5; }
        .tab-btn { flex: 1; border: none; background: transparent; cursor: pointer; font-weight: 700; color: #555; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }
        .tab-btn.active { background: #ffca28; color: #000; }
        
        .content-area { flex: 1; overflow: hidden; position: relative; display: flex; flex-direction: column; }
        .tab-content { display: none; width: 100%; height: 100%; overflow-y: auto; }
        .tab-content.active { display: block; }
        
        /* ANALISIS */
        .markdown-wrapper { padding: 50px; max-width: 900px; margin: auto; background: white; min-height: 100%; box-shadow: 0 0 20px rgba(0,0,0,0.05); }
        .markdown-body { font-size: 16px; line-height: 1.8; color: #333; padding-bottom: 50px; }
        .markdown-body h1 { color: #000; background: #ffeb3b; display: inline-block; padding: 5px 15px; transform: rotate(-1deg); margin-bottom: 30px; }
        .markdown-body h2 { color: #333; border-bottom: 3px solid #ffca28; padding-bottom: 5px; margin-top: 40px; }
        
        /* INFOGRAFIA NANOBANANA STYLE */
        #infografia-wrapper { padding: 50px; text-align: center; min-height: 100%; background: #eceff1; }
        #infografia-visual-container { 
            width: 900px; margin: 0 auto; background: white; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.3); 
            text-align: left; overflow: visible; display: inline-block; 
        }
        
        /* Clases que la IA debe usar */
        .poster-header { background: #ffd600; color: #000; padding: 60px 50px; position: relative; clip-path: polygon(0 0, 100% 0, 100% 85%, 0 100%); }
        .poster-title { font-size: 48px; font-weight: 900; margin: 0; line-height: 1; text-transform: uppercase; letter-spacing: -1px; }
        .poster-meta { margin-top: 20px; font-size: 16px; font-weight: 700; opacity: 0.8; letter-spacing: 1px; }
        
        .poster-body { padding: 40px 50px 80px 50px; }
        .section-title { font-size: 24px; font-weight: 900; color: #000; background: #ffeb3b; display: inline-block; padding: 5px 15px; margin: 40px 0 20px 0; transform: skew(-10deg); }
        
        .traffic-container { display: flex; gap: 20px; }
        .traffic-col { flex: 1; padding: 20px; border: 2px solid #000; border-radius: 10px; background: #fff; box-shadow: 5px 5px 0px #000; }
        .traffic-title { font-weight: 900; font-size: 18px; text-transform: uppercase; margin-bottom: 15px; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        
        .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
        .metric-card { background: #212121; color: #ffeb3b; padding: 30px; border-radius: 10px; text-align: center; box-shadow: 5px 5px 0px #9e9e9e; }
        .metric-val { display: block; font-size: 42px; font-weight: 900; }
        .metric-lbl { font-size: 14px; font-weight: 700; text-transform: uppercase; }
        
        .poster-mermaid { margin-top: 30px; border: 2px dashed #ccc; padding: 20px; text-align: center; border-radius: 10px; }

        /* UI */
        button { cursor: pointer; padding: 8px 16px; border-radius: 4px; border: none; font-weight: 600; font-size: 13px; }
        .btn-control { background: #fff; color: #333; }
        .btn-primary { background: #ffd600; color: #000; margin-left: auto; display: none; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        .btn-pdf { background: #c5221f; color: white; text-decoration: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; display: none; }
        
        /* CHAT */
        #tab-chat { display: none; width: 100%; height: 100%; flex-direction: column; }
        .chat-input-box { height: 90px; padding: 20px; background: #212121; display: flex; gap: 15px; flex-shrink: 0; align-items: center; }
        #chat-history { flex: 1; overflow-y: auto; padding: 40px; background: #fff; display: flex; flex-direction: column; gap: 25px; }
        .msg { padding: 20px; border-radius: 15px; font-size: 15px; line-height: 1.6; max-width: 80%; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .msg.user { background: #fff9c4; color: #000; align-self: flex-end; border-bottom-right-radius: 2px; border: 1px solid #ffecb3; }
        .msg.ai { background: #f5f5f5; color: #333; align-self: flex-start; border-bottom-left-radius: 2px; }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button class="btn-control" onclick="ajustarZoom(-0.2)">➖</button>
                <span id="zoom-level" style="color:white; font-size:12px; margin:0 10px;">100%</span>
                <button class="btn-control" onclick="ajustarZoom(0.2)">➕</button>
            </div>
            <div id="pdf-container" class="pdf-scroll-container"></div>
        </div>
        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="abrirPestana('tab-analisis')">📝 Análisis</button>
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">🍌 NanoBanana Póster</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">💬 Chat</button>
                <button id="btn-save-img" class="btn-primary" onclick="descargarPoster()">📸 Guardar Imagen</button>
            </div>
            <div class="content-area">
                <div id="tab-analisis" class="tab-content active"><div class="markdown-wrapper"><div id="analisis-content" class="markdown-body"></div></div></div>
                <div id="tab-infografia" class="tab-content"><div id="infografia-wrapper"><div id="infografia-visual-container"></div></div></div>
                <div id="tab-chat" class="tab-content">
                    <div class="chat-input-box">
                        <input type="text" id="user-input" placeholder="Pregunta sobre el documento..." style="flex:1; padding:15px; border:none; border-radius:4px; outline:none; font-size:16px;" onkeypress="if(event.key==='Enter') enviarMensaje()">
                        <button onclick="enviarMensaje()" style="background:#ffca28; color:#000; padding:12px 30px; border-radius:4px; border:none; font-weight:bold; cursor:pointer;">ENVIAR</button>
                    </div>
                    <div id="chat-history"></div>
                </div>
            </div>
        </div>
    </div>
    <script>
        const API_KEY = "__API_KEY__"; 
        const MODELS = __MODELS_JSON__; 
        
        let pdfDoc = null, scale = 1.0, rotation = 0, globalPdfBase64 = null;
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
                
                // INYECCIÓN HTML SEGURA
                if(DATA_INFO && DATA_INFO !== "null") {
                    document.getElementById('infografia-visual-container').innerHTML = DATA_INFO;
                    
                    // Inyectar gráfico mermaid SI existe placeholder
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
            const hasContent = document.querySelector('.poster-title');
            btn.style.display = (id === 'tab-infografia' && hasContent) ? 'block' : 'none';
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
                const viewport = page.getViewport({ scale: scale, rotation: rotation });
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
            h.innerHTML += `<div id="${loadingId}" class="msg ai" style="color:#888">Thinking...</div>`;
            
            async function tryFetch(prompt, attempts = 0) {
                if (attempts >= MODELS.length) throw new Error("Todos los modelos fallaron.");
                const currentModel = MODELS[attempts];
                
                // PROMPT ESTRICTO
                const strictPrompt = "Actúa como NanoBanana AI, experto médico. TU OBJETIVO: Responder a la pregunta del usuario USANDO ÚNICAMENTE LA INFORMACIÓN DEL PDF ADJUNTO. Si la respuesta no está en el PDF, indica que no se encuentra en el documento. Pregunta: " + prompt;

                try {
                    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${currentModel}:generateContent?key=${API_KEY}`, {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ contents: [{ parts: [{ text: strictPrompt }, { inline_data: { mime_type: "application/pdf", data: globalPdfBase64 } }] }] })
                    });
                    if (!r.ok) throw new Error(r.statusText);
                    const d = await r.json();
                    if(d.error) throw new Error(d.error.message);
                    return d.candidates[0].content.parts[0].text;
                } catch(e) {
                    return await tryFetch(prompt, attempts + 1);
                }
            }

            try {
                const text = await tryFetch(t);
                document.getElementById(loadingId).remove();
                h.innerHTML += `<div class="msg ai">${marked.parse(text)}</div>`;
            } catch(e) { document.getElementById(loadingId).innerHTML = "Error de conexión."; }
            h.scrollTop = h.scrollHeight;
        }

        function descargarPoster() {
            const el = document.getElementById('infografia-visual-container');
            html2canvas(el, { scale: 3, windowWidth: el.scrollWidth, windowHeight: el.scrollHeight, backgroundColor: "#ffffff" }).then(canvas => {
                const a = document.createElement('a'); a.download = 'NanoBanana_Poster.png'; a.href = canvas.toDataURL('image/png'); a.click();
            });
        }
    </script>
</body>
</html>
"""

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2913/2913465.png", width=50) # Logo Placeholder
    st.header("Biblioteca NanoBanana")
    st.caption(f"🚀 Motor: {REAL_MODELS_PYTHON[0].replace('models/', '')}")
    
    modo_admin = st.checkbox("Modo Administrador")
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

def clean_html_output(text):
    # Quitar bloques de markdown ```html ... ```
    text = text.replace("```html", "").replace("```", "")
    # Quitar etiquetas html y body si la IA las pone (queremos solo el div interior)
    text = text.replace("<!DOCTYPE html>", "").replace("<html>", "").replace("</html>", "").replace("<body>", "").replace("</body>", "")
    return text.strip()

if modo_admin:
    st.title("⚙️ Cargar Nueva Guía (Admin)")
    uploaded_file = st.file_uploader("Subir PDF", type="pdf")
    
    if uploaded_file and st.button("🚀 Procesar con NanoBanana AI"):
        with st.spinner("Analizando y Diseñando..."):
            pdf_bytes = uploaded_file.read()
            
            def try_generate_dynamic(prompt_text, file_bytes):
                for m_name in REAL_MODELS_PYTHON:
                    try:
                        model = genai.GenerativeModel(m_name)
                        response = model.generate_content([{'mime_type': 'application/pdf', 'data': file_bytes}, prompt_text])
                        return response.text
                    except Exception as e:
                        time.sleep(1)
                        continue
                raise Exception("Fallo total. Ningún modelo disponible respondió.")
            
            try:
                # 1. ANÁLISIS
                analisis_txt = try_generate_dynamic("ERES UN ASISTENTE MÉDICO. Analiza la guía y extrae: 1.Definiciones clave 2.Algoritmo de manejo 3.Dosis/Fármacos 4.Criterios de ingreso. Formato Markdown limpio.", pdf_bytes)
                
                # 2. HTML VISUAL (NANOBANANA STYLE)
                prompt_html = """
                Actúa como Diseñador Web Senior. Genera SOLO el código HTML (sin markdown) para un póster médico moderno 'NanoBanana Style'.
                Usa ESTRICTAMENTE esta estructura con estas clases (ya tengo el CSS definido):
                
                <div class="poster-header">
                    <h1 class="poster-title">[TÍTULO CORTO DE LA GUÍA]</h1>
                    <div class="poster-meta">[SOCIEDAD] • [AÑO]</div>
                </div>
                <div class="poster-body">
                    <div class="section-title">SEMÁFORO DE ACCIÓN</div>
                    <div class="traffic-container">
                       <div class="traffic-col tc-stop"><div class="traffic-title">⛔ NO HACER</div><ul><li>...</li></ul></div>
                       <div class="traffic-col tc-wait"><div class="traffic-title">⚠️ PRECAUCIÓN</div><ul><li>...</li></ul></div>
                       <div class="traffic-col tc-go"><div class="traffic-title">✅ RECOMENDADO</div><ul><li>...</li></ul></div>
                    </div>

                    <div class="section-title">DATOS CLAVE</div>
                    <div class="metrics-grid">
                        <div class="metric-card"><span class="metric-val">[Dato 1]</span><span class="metric-lbl">[Etiqueta]</span></div>
                        <div class="metric-card"><span class="metric-val">[Dato 2]</span><span class="metric-lbl">[Etiqueta]</span></div>
                        <div class="metric-card"><span class="metric-val">[Dato 3]</span><span class="metric-lbl">[Etiqueta]</span></div>
                    </div>

                    <div class="section-title">ALGORITMO</div>
                    <div id="mermaid-placeholder" class="poster-mermaid"></div>
                </div>
                """
                raw_html = try_generate_dynamic(prompt_html, pdf_bytes)
                info_html = clean_html_output(raw_html)
                
                # 3. MERMAID
                mermaid_code = try_generate_dynamic("Crea un diagrama 'mermaid graph TD' SIMPLE (max 6 nodos) resumiendo el flujo principal. Usa textos muy cortos entre comillas. Solo código.", pdf_bytes).replace("```mermaid", "").replace("```", "")
                
                st.session_state['temp_upload'] = {
                    'titulo': uploaded_file.name,
                    'bytes': pdf_bytes,
                    'analisis': analisis_txt,
                    'html': info_html,
                    'mermaid': mermaid_code
                }
                st.success("¡Procesado!")
                
            except Exception as e:
                st.error(f"Error IA: {str(e)}")

    if 'temp_upload' in st.session_state:
        st.write("---")
        titulo_final = st.text_input("Título", value=st.session_state['temp_upload']['titulo'])
        if st.button("💾 Guardar en Biblioteca"):
            guardar_guia(titulo_final, st.session_state['temp_upload']['bytes'], st.session_state['temp_upload']['analisis'], st.session_state['temp_upload']['html'], st.session_state['temp_upload']['mermaid'])
            del st.session_state['temp_upload']
            st.success("Guardado.")
            st.rerun()

else:
    if 'active_guide_id' in st.session_state:
        guia = obtener_guia_por_id(st.session_state['active_guide_id'])
        if guia:
            g_pdf_b64 = base64.b64encode(guia[3]).decode('utf-8')
            g_analisis = guia[4].replace("`", "\`").replace("${", "\${")
            g_html = guia[5].replace("`", "\`")
            g_mermaid = guia[6].replace("`", "\`")
            
            final_html = html_template.replace("__API_KEY__", API_KEY)
            final_html = final_html.replace("__MODELS_JSON__", json.dumps(REAL_MODELS_JS))
            final_html = final_html.replace("__PDF_DATA__", g_pdf_b64)
            final_html = final_html.replace("__ANALISIS_DATA__", g_analisis)
            final_html = final_html.replace("__INFO_DATA__", g_html)
            final_html = final_html.replace("__MERMAID_DATA__", g_mermaid)
            
            components.html(final_html, height=1000, scrolling=False)
    else:
        st.title("Bienvenido a NanoBanana Medical")
        st.info("👈 Selecciona una guía para empezar.")
