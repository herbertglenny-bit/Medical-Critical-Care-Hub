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

# --- 2. MOTOR IA (SISTEMA DE AHORRO DE CUOTA) ---
def get_ia_engine():
    try:
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("⚠️ Configura GEMINI_API_KEY en Secrets.")
            st.stop()
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Intentamos usar el modelo flash más estable
        valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        name = next((m for m in valid_models if "1.5-flash" in m), valid_models[0])
        return genai.GenerativeModel(model_name=name), name
    except Exception as e:
        return None, None

model_ia, active_model_name = get_ia_engine()

# --- 3. BASE DE DATOS ---
def get_db():
    conn = sqlite3.connect('guias_medicas.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS guias 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         titulo TEXT, fecha TEXT, pdf_blob BLOB, 
                         analisis_md TEXT, infografia_html TEXT)''')

def clean_filename(filename):
    name = re.sub(r'\.[Pp][Dd][Ff]$', '', filename)
    name = name.replace('-', ' ').replace('_', ' ')
    return name.title()

init_db()

# --- 4. PLANTILLA HTML V76 (PANELES INDEPENDIENTES) ---
html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script>pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';</script>
    <style>
        :root { --banana: #ffd600; --dark: #323639; }
        body, html { margin:0; padding:0; height:100vh; font-family:'Inter', sans-serif; background:#fff; overflow:hidden; }
        .main { display:flex; height:100vh; width:100vw; }
        
        /* PDF SIDE (SCROLL H/V) */
        .pdf-side { width:50%; height:100%; display:flex; flex-direction:column; background:#525659; border-right:2px solid #000; }
        .toolbar { height:50px; background:var(--dark); display:flex; align-items:center; justify-content:center; gap:20px; color:white; }
        .viewport { flex:1; overflow:auto; padding:20px; }
        .pdf-canvas-container { min-width: fit-content; margin: 0 auto; display: flex; flex-direction: column; align-items: center; }
        canvas { box-shadow:0 10px 30px rgba(0,0,0,0.5); margin-bottom:20px; background:white; }

        /* DATA SIDE */
        .data-side { width:50%; height:100%; display:flex; flex-direction:column; background:white; }
        .tabs { display:flex; background:#f1f3f4; border-bottom:1px solid #ddd; height:50px; }
        .tab-btn { flex:1; border:none; cursor:pointer; font-weight:bold; font-size:11px; text-transform:uppercase; color:#5f6368; }
        .tab-btn.active { background:white; color:black; border-bottom:4px solid var(--banana); }
        .tab-content { display:none; flex:1; overflow-y:auto; padding:35px; box-sizing:border-box; background:white; }
        .tab-content.active { display:block; }
        
        #chat-log { height:400px; overflow-y:auto; border:1px solid #eee; padding:15px; background:#f9f9f9; border-radius:8px; margin-bottom:10px; }
    </style>
</head>
<body>
    <div class="main">
        <div class="pdf-side">
            <div class="toolbar">
                <button onclick="zoom(-0.2)" style="cursor:pointer; border:none; background:#444; color:white; padding:5px 10px; border-radius:4px;">➖</button>
                <span id="z-txt">110%</span>
                <button onclick="zoom(0.2)" style="cursor:pointer; border:none; background:#444; color:white; padding:5px 10px; border-radius:4px;">➕</button>
                <span id="p-txt" style="font-size:12px; margin-left:10px;">Pág: 1 / -</span>
                <button onclick="download()" style="background:var(--banana); border:none; padding:5px 10px; border-radius:4px; font-weight:bold; cursor:pointer;">📥 DESCARGAR</button>
            </div>
            <div id="pdf-viewport" class="viewport" onscroll="updatePage()">
                <div id="pdf-inner" class="pdf-canvas-container"></div>
            </div>
        </div>
        <div class="data-side">
            <div class="tabs">
                <button class="tab-btn active" onclick="openTab(event, 'analisis')">Análisis GPC</button>
                <button class="tab-btn" onclick="openTab(event, 'poster')">Póster UCI</button>
                <button class="tab-btn" onclick="openTab(event, 'chat')">Chat Experto</button>
            </div>
            <div id="analisis" class="tab-content active">
                <h1 id="title-out" style="font-weight:900; border-bottom:2px solid #eee; padding-bottom:10px;"></h1>
                <div id="md-out" style="line-height:1.6; margin-top:20px;"></div>
            </div>
            <div id="poster" class="tab-content"><div id="html-out"></div></div>
            <div id="chat" class="tab-content">
                <div id="chat-log"></div>
                <div style="display:flex; gap:10px;">
                    <input type="text" id="c-in" style="flex:1; padding:12px; border:1px solid #ddd;" placeholder="Consulta técnica...">
                    <button onclick="ask()" style="padding:12px; background:black; color:white; border:none; cursor:pointer;">ENVIAR</button>
                </div>
            </div>
        </div>
    </div>
    <script>
        const API_KEY = "__API_KEY__";
        const MODEL = "__MODEL__";
        const PDF_B64 = "__PDF_B64__";
        const G = __GUIA_JSON__;
        
        let pdfDoc = null, scale = 1.1;

        window.onload = () => {
            document.getElementById('title-out').innerText = G.titulo;
            document.getElementById('md-out').innerHTML = marked.parse(G.analisis);
            document.getElementById('html-out').innerHTML = G.infografia;
            if(PDF_B64) initPDF(PDF_B64);
        };

        async function initPDF(data) {
            const loadingTask = pdfjsLib.getDocument({data: atob(data)});
            pdfDoc = await loadingTask.promise;
            document.getElementById('p-txt').innerText = `Pág: 1 / ${pdfDoc.numPages}`;
            draw();
        }

        async function draw() {
            const view = document.getElementById('pdf-inner'); view.innerHTML = "";
            document.getElementById('z-txt').innerText = Math.round(scale*100) + "%";
            for(let i=1; i<=pdfDoc.numPages; i++) {
                const page = await pdfDoc.getPage(i);
                const vp = page.getViewport({scale});
                const can = document.createElement('canvas');
                can.height = vp.height; can.width = vp.width;
                view.appendChild(can);
                await page.render({canvasContext: can.getContext('2d'), viewport: vp}).promise;
            }
        }

        function zoom(v) { scale = Math.max(0.4, scale + v); draw(); }

        function updatePage() {
            const cans = document.getElementsByTagName('canvas');
            const vTop = document.getElementById('pdf-viewport').scrollTop;
            for(let i=0; i<cans.length; i++) {
                if(cans[i].offsetTop >= vTop) {
                    document.getElementById('p-txt').innerText = `Pág: ${i+1} / ${pdfDoc.numPages}`;
                    break;
                }
            }
        }

        function download() {
            const a = document.createElement('a'); a.href = "data:application/pdf;base64," + PDF_B64;
            a.download = G.titulo + ".pdf"; a.click();
        }

        function openTab(e, id) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            e.currentTarget.classList.add('active');
        }

        async function ask() {
            const inp = document.getElementById('c-in'), log = document.getElementById('chat-log');
            const txt = inp.value; if(!txt) return;
            log.innerHTML += `<div style="margin-bottom:10px;"><b>Médico:</b> ${txt}</div>`; inp.value = "";
            try {
                const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${API_KEY}`, {
                    method:'POST', headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({contents:[{parts:[{text: "Responde de forma técnica sobre el PDF: " + txt},{inline_data:{mime_type:"application/pdf", data:PDF_B64}}]}]})
                });
                const d = await r.json();
                const res = d.candidates[0].content.parts[0].text;
                log.innerHTML += `<div style="color:#2c3e50; border-left:3px solid var(--banana); padding-left:10px; margin-bottom:20px;"><b>IA:</b> ${marked.parse(res)}</div>`;
                log.scrollTop = log.scrollHeight;
            } catch(e) { log.innerHTML += "<div>Límite de peticiones alcanzado. Intenta de nuevo en 1 minuto.</div>"; }
        }
    </script>
</body>
</html>
"""

# --- 5. LÓGICA STREAMLIT ---
with st.sidebar:
    st.title("🍌 NanoBanana UCI")
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    
    with get_db() as conn:
        guias = conn.execute('SELECT id, titulo FROM guias ORDER BY id DESC').fetchall()
    
    for g in guias:
        c1, c2 = st.columns([0.8, 0.2])
        if c1.button(f"📄 {g['titulo']}", key=f"v_{g['id']}", use_container_width=True):
            st.session_state['active_id'] = g['id']
            st.rerun()
        if modo_admin and c2.button("🗑️", key=f"d_{g['id']}"):
            with get_db() as conn:
                conn.execute('DELETE FROM guias WHERE id = ?', (g['id'],))
            st.rerun()

if modo_admin:
    st.header("⚙️ Gestión de GPC")
    file = st.file_uploader("Subir PDF", type="pdf")
    
    if file and st.button("🚀 PROCESAR GUÍA"):
        with st.spinner("Analizando evidencias (ahorrando cuota de IA)..."):
            pdf_bytes = file.read()
            clean_title = clean_filename(file.name)
            
            # --- COMBO PROMPT (2 EN 1 PARA AHORRAR PETICIONES) ---
            p_combo = """Analiza este PDF en ESPAÑOL. 
            Devuelve el resultado en formato JSON con dos campos:
            1. "analisis": Un resumen técnico profundo (Metodología, Delta, Bundles, Dosificación, Perlas).
            2. "poster": Un fragmento de DIV HTML profesional para póster UCI (Blanco, Negro, Amarillo, Semáforo).
            No incluyas saludos ni texto fuera del JSON."""
            
            try:
                response = model_ia.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p_combo])
                raw_data = response.text.replace("```json", "").replace("```", "").strip()
                data_json = json.loads(raw_data)
                
                with get_db() as conn:
                    conn.execute('INSERT INTO guias (titulo, fecha, pdf_blob, analisis_md, infografia_html) VALUES (?,?,?,?,?)',
                                 (clean_title, datetime.now().strftime("%Y-%m-%d"), pdf_bytes, data_json['analisis'], data_json['poster']))
                st.success("✅ Guía integrada con éxito.")
                st.rerun()
            except Exception as e:
                if "429" in str(e):
                    st.error("❌ Has alcanzado el límite de peticiones de Google por hoy (20/día). Espera 24h o usa otra API Key.")
                else:
                    st.error(f"Error técnico: {e}")

elif 'active_id' in st.session_state:
    with get_db() as conn:
        g = conn.execute('SELECT * FROM guias WHERE id = ?', (st.session_state['active_id'],)).fetchone()
    
    if g:
        pdf_b64 = base64.b64encode(g['pdf_blob']).decode('utf-8')
        g_json = {"titulo": g['titulo'], "analisis": g['analisis_md'], "infografia": g['infografia_html']}
        
        render = html_template.replace("__API_KEY__", st.secrets["GEMINI_API_KEY"])
        js_model = active_model_name.replace("models/", "")
        render = render.replace("__MODEL__", js_model)
        render = render.replace("__PDF_B64__", pdf_b64)
        render = render.replace("__GUIA_JSON__", json.dumps(g_json))
        
        components.html(render, height=1200, scrolling=False)
else:
    st.info("👈 Selecciona una guía técnica del panel lateral.")
