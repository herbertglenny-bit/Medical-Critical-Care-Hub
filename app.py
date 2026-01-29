import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import base64
from datetime import datetime
import google.generativeai as genai
import time

# Configuración
st.set_page_config(page_title="Biblioteca Médica IA", layout="wide", initial_sidebar_state="expanded")

# --- SEGURIDAD ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except (FileNotFoundError, KeyError):
    st.error("⚠️ Error: Falta 'GEMINI_API_KEY' en Secrets.")
    st.stop()

# --- EL CHIVATO (DIAGNÓSTICO) ---
# Esto nos dirá la verdad sobre qué está instalado
version_actual = genai.__version__

with st.sidebar:
    st.divider()
    st.subheader("🕵️‍♂️ DIAGNÓSTICO TÉCNICO")
    st.info(f"Versión Librería Google: {version_actual}")
    
    if version_actual < "0.7.0":
        st.error("❌ ERROR CRÍTICO: La librería es muy antigua. El archivo 'requirements.txt' no se está leyendo o tiene el nombre mal escrito.")
    else:
        st.success("✅ La librería está actualizada. El problema es otro.")
    st.divider()

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

# --- HTML TEMPLATE ---
html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Estación Médica V45</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    <script>pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';</script>
    <style>
        * { box-sizing: border-box; }
        body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; font-family: 'Segoe UI', Roboto, sans-serif; background: #202124; }
        .main-container { display: flex; width: 100vw; height: 100vh; }
        .pdf-section { width: 50%; min-width: 50%; height: 100%; display: flex; flex-direction: column; border-right: 1px solid #444; background: #525659; }
        .pdf-toolbar { height: 50px; background: #323639; display: flex; align-items: center; justify-content: center; gap: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); z-index: 10; flex-shrink: 0; }
        .pdf-scroll-container { flex: 1; overflow: auto; padding: 40px; background: #525659; text-align: center; display: block; }
        .pdf-page-canvas { display: inline-block; box-shadow: 0 4px 15px rgba(0,0,0,0.6); margin-bottom: 20px; vertical-align: top; background: white; }
        .right-panel { width: 50%; min-width: 50%; height: 100%; display: flex; flex-direction: column; background: #f0f2f5; }
        .tabs-header { height: 50px; background: #fff; border-bottom: 1px solid #ddd; display: flex; flex-shrink: 0; z-index: 5; }
        .tab-btn { flex: 1; border: none; background: transparent; cursor: pointer; font-weight: 600; color: #5f6368; font-size: 14px; border-bottom: 3px solid transparent; }
        .tab-btn.active { color: #1a73e8; border-bottom: 3px solid #1a73e8; background: #e8f0fe; }
        .content-area { flex: 1; overflow: hidden; position: relative; display: flex; flex-direction: column; }
        .tab-content { display: none; width: 100%; height: 100%; overflow-y: auto; }
        .tab-content.active { display: block; }
        .markdown-wrapper { padding: 40px; max-width: 900px; margin: auto; background: white; min-height: 100%; }
        .markdown-body { font-size: 16px; line-height: 1.7; color: #2c3e50; padding-bottom: 50px; }
        .markdown-body h1 { color: #1565c0; border-bottom: 2px solid #eee; margin-top: 0; }
        .markdown-body h2 { color: #2c3e50; margin-top: 30px; border-left: 4px solid #1565c0; padding-left: 10px; }
        #infografia-wrapper { padding: 50px; text-align: center; min-height: 100%; background: #dce1e6; }
        #infografia-visual-container { width: 900px; margin: 0 auto; background: white; box-shadow: 0 15px 50px rgba(0,0,0,0.2); font-family: 'Roboto', sans-serif; color: #333; text-align: left; overflow: visible; display: inline-block; }
        .poster-header { background: #003c8f; color: white; padding: 50px; position: relative; }
        .poster-header:after { content: ""; display: block; width: 100%; height: 10px; background: #ffca28; position: absolute; bottom: 0; left: 0; }
        .poster-title { font-size: 38px; font-weight: 900; margin: 0; line-height: 1.1; text-transform: uppercase; letter-spacing: -0.5px; }
        .poster-meta { margin-top: 15px; font-size: 13px; font-weight: 300; opacity: 0.9; display: flex; gap: 20px; text-transform: uppercase; letter-spacing: 1px; }
        .poster-body { padding: 50px; display: flex; flex-direction: column; gap: 40px; }
        .section-title { font-size: 18px; font-weight: 900; color: #555; text-transform: uppercase; border-left: 5px solid #003c8f; padding-left: 10px; margin-bottom: 20px; }
        .traffic-container { display: flex; gap: 20px; align-items: stretch; }
        .traffic-col { flex: 1; padding: 25px; border-radius: 8px; position: relative; }
        .tc-stop { background: #fce8e6; border: 1px solid #fad2cf; } .tc-stop .traffic-title { color: #c5221f; }
        .tc-wait { background: #fef7e0; border: 1px solid #fce8b2; } .tc-wait .traffic-title { color: #f29900; }
        .tc-go { background: #e6f4ea; border: 1px solid #ceead6; } .tc-go .traffic-title { color: #137333; }
        .traffic-icon { font-size: 30px; margin-bottom: 10px; display: block; }
        .traffic-title { font-weight: 900; font-size: 16px; margin-bottom: 10px; text-transform: uppercase; }
        .traffic-col ul { padding-left: 15px; margin: 0; }
        .traffic-col li { margin-bottom: 8px; font-size: 14px; line-height: 1.4; color: #444; }
        .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
        .metric-card { background: #003c8f; color: white; padding: 25px; border-radius: 8px; text-align: center; }
        .metric-val { display: block; font-size: 36px; font-weight: 900; margin-bottom: 5px; }
        .metric-lbl { font-size: 12px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.8; font-weight: 600; }
        .poster-mermaid { background: #f8f9fa; padding: 30px; border-radius: 8px; border: 1px solid #eee; text-align: center; }
        .poster-footer { background: #202124; color: white; padding: 40px 50px; text-align: center; }
        .footer-list { display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; }
        .footer-item { background: rgba(255,255,255,0.15); padding: 10px 20px; border-radius: 30px; font-size: 14px; font-weight: 500; }
        button { cursor: pointer; padding: 8px 16px; border-radius: 4px; border: none; font-weight: 600; font-size: 13px; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
        .btn-control { background: #fff; color: #333; }
        .btn-primary { background: #0d47a1; color: white; margin-left: auto; display: none; }
        .btn-pdf { background: #c5221f; color: white; text-decoration: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; display: none; }
        #tab-chat { display: none; width: 100%; height: 100%; flex-direction: column; }
        .chat-layout { display: flex; flex-direction: column; height: 100%; }
        .chat-input-box { height: 80px; padding: 20px; background: #fff; border-bottom: 1px solid #eee; display: flex; gap: 15px; flex-shrink: 0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); z-index: 10; }
        #chat-history { flex: 1; overflow-y: auto; padding: 30px; background: #f8f9fa; display: flex; flex-direction: column; gap: 20px; }
        .msg { padding: 15px 20px; border-radius: 12px; font-size: 15px; line-height: 1.6; max-width: 85%; }
        .msg.user { background: #e3f2fd; color: #1565c0; align-self: flex-end; }
        .msg.ai { background: #fff; border: 1px solid #e0e0e0; align-self: flex-start; }
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
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">🎨 Infografía Visual</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">💬 Chat</button>
                <button id="btn-save-img" class="btn-primary" onclick="descargarPoster()">📸 Descargar Imagen</button>
            </div>
            <div class="content-area">
                <div id="tab-analisis" class="tab-content active"><div class="markdown-wrapper"><div id="analisis-content" class="markdown-body"></div></div></div>
                <div id="tab-infografia" class="tab-content"><div id="infografia-wrapper"><div id="infografia-visual-container"></div></div></div>
                <div id="tab-chat" class="tab-content">
                    <div class="chat-input-box">
                        <input type="text" id="user-input" placeholder="Escribe tu pregunta..." style="flex:1; padding:12px 20px; border:1px solid #ddd; border-radius:30px; outline:none; font-size:15px; background:#f9f9f9;" onkeypress="if(event.key==='Enter') enviarMensaje()">
                        <button onclick="enviarMensaje()" style="background:#1565c0; color:white; padding:0 25px; border-radius:30px; border:none; font-weight:bold; cursor:pointer;">ENVIAR</button>
                    </div>
                    <div id="chat-history"></div>
                </div>
            </div>
        </div>
    </div>
    <script>
        const API_KEY = "__API_KEY__"; 
        // V45: Lista actualizada con nombres explícitos y modernos
        const MODELS = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"];
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
                if(DATA_INFO && DATA_INFO !== "null") {
                    document.getElementById('infografia-visual-container').innerHTML = DATA_INFO;
                    if(DATA_MERMAID && DATA_MERMAID !== "null") {
                        setTimeout(() => { const target = document.getElementById('mermaid-placeholder'); if(target) { target.innerHTML = `<div class="mermaid">${DATA_MERMAID}</div>`; mermaid.run(); } }, 500);
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
            h.innerHTML += `<div id="${loadingId}" class="msg ai" style="color:#888">...</div>`;
            
            async function tryFetch(prompt, attempts = 0) {
                if (attempts >= MODELS.length) throw new Error("Todos los modelos fallaron.");
                const currentModel = MODELS[attempts];
                try {
                    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${currentModel}:generateContent?key=${API_KEY}`, {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ contents: [{ parts: [{ text: "Responde como médico experto. Breve: " + prompt }, { inline_data: { mime_type: "application/pdf", data: globalPdfBase64 } }] }] })
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
            } catch(e) { document.getElementById(loadingId).innerHTML = "Error de red/IA."; }
            h.scrollTop = h.scrollHeight;
        }

        function descargarPoster() {
            const el = document.getElementById('infografia-visual-container');
            html2canvas(el, { scale: 3, windowWidth: el.scrollWidth, windowHeight: el.scrollHeight, backgroundColor: "#ffffff" }).then(canvas => {
                const a = document.createElement('a'); a.download = 'Infografia_Medica.png'; a.href = canvas.toDataURL('image/png'); a.click();
            });
        }
    </script>
</body>
</html>
"""

# --- SIDEBAR ---
with st.sidebar:
    st.header("🏥 Biblioteca")
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

if modo_admin:
    st.title("⚙️ Administrador: Cargar Nueva Guía")
    uploaded_file = st.file_uploader("Subir PDF", type="pdf")
    
    if uploaded_file and st.button("🚀 Procesar con IA"):
        with st.spinner("Procesando... esto puede tardar unos segundos..."):
            genai.configure(api_key=API_KEY)
            pdf_bytes = uploaded_file.read()
            
            # --- FUNCIÓN DE SEGURIDAD V45 ---
            def try_generate(prompt_text, file_bytes):
                # Probamos los nombres viejos y nuevos
                models_to_try = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro", "gemini-pro"]
                last_error = ""
                for m_name in models_to_try:
                    try:
                        model = genai.GenerativeModel(m_name)
                        response = model.generate_content([{'mime_type': 'application/pdf', 'data': file_bytes}, prompt_text])
                        return response.text, m_name
                    except Exception as e:
                        last_error = str(e)
                        time.sleep(1)
                        continue
                raise Exception(f"Fallo total en IA: {last_error}")
            
            try:
                analisis_txt, used_model = try_generate("ERES UN MOTOR DE DATOS. EMPIEZA DIRECTO CON EL TÍTULO (#). Analiza: 1.Definiciones 2.Algoritmo 3.Soporte 4.Semáforo 5.Poblaciones.", pdf_bytes)
                st.info(f"Análisis completado con: {used_model}")
                
                info_html, _ = try_generate("""Genera SOLO HTML para PÓSTER MÉDICO (Diseño V31). 
                <div class="poster-header"><h1 class="poster-title">TITULO</h1><div class="poster-meta">META</div></div>
                <div class="poster-body">...contenido estructurado...<div id="mermaid-placeholder" class="poster-mermaid"></div></div>
                <div class="poster-footer">...</div>""", pdf_bytes)
                info_html = info_html.replace("```html", "").replace("```", "")
                
                mermaid_code, _ = try_generate("Crea 'mermaid graph TD' SIMPLE. Solo código.", pdf_bytes)
                mermaid_code = mermaid_code.replace("```mermaid", "").replace("```", "")
                
                st.session_state['temp_upload'] = {
                    'titulo': uploaded_file.name,
                    'bytes': pdf_bytes,
                    'analisis': analisis_txt,
                    'html': info_html,
                    'mermaid': mermaid_code
                }
                st.success("Procesado con éxito.")
                
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
            final_html = final_html.replace("__PDF_DATA__", g_pdf_b64)
            final_html = final_html.replace("__ANALISIS_DATA__", g_analisis)
            final_html = final_html.replace("__INFO_DATA__", g_html)
            final_html = final_html.replace("__MERMAID_DATA__", g_mermaid)
            
            components.html(final_html, height=1000, scrolling=False)
    else:
        st.title("Bienvenido")
        st.info("👈 Selecciona una guía.")
