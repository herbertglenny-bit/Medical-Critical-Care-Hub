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

# --- 2. MOTOR IA (AUTODETECCIÓN DE MODELO) ---
def get_ia_engine():
    try:
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("⚠️ Configura GEMINI_API_KEY en Secrets.")
            st.stop()
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Buscamos el nombre exacto que el servidor de Google acepta hoy
        valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        name = next((m for m in valid_models if "1.5-flash" in m), valid_models[0])
        return genai.GenerativeModel(model_name=name), name
    except Exception as e:
        st.error(f"Error de conexión con la API de Google: {e}")
        return None, None

model_ia, active_model_name = get_ia_engine()

# --- 3. BASE DE DATOS (ACCESO POR NOMBRE) ---
def get_db():
    conn = sqlite3.connect('guias_medicas.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row # Esto evita el error g[5]
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS guias 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         titulo TEXT, autor TEXT, revista TEXT, fecha_pub TEXT, 
                         pdf_blob BLOB, analisis_md TEXT, infografia_html TEXT)''')
init_db()

# --- 4. PLANTILLA HTML MAESTRA V69 ---
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
        
        /* VISOR PDF */
        .pdf-side { width:50%; height:100%; display:flex; flex-direction:column; background:#525659; border-right:2px solid #000; }
        .toolbar { height:50px; background:var(--dark); display:flex; align-items:center; justify-content:center; gap:20px; color:white; }
        .viewport { flex:1; overflow:auto; padding:20px; display:flex; flex-direction:column; align-items:center; }
        canvas { box-shadow:0 10px 30px rgba(0,0,0,0.5); margin-bottom:20px; background:white; }

        /* PANELES DE DATOS */
        .data-side { width:50%; height:100%; display:flex; flex-direction:column; background:white; }
        .tabs { display:flex; background:#f1f3f4; border-bottom:1px solid #ddd; height:50px; }
        .tab-btn { flex:1; border:none; cursor:pointer; font-weight:bold; font-size:11px; text-transform:uppercase; color:#5f6368; }
        .tab-btn.active { background:white; color:black; border-bottom:4px solid var(--banana); }
        
        .tab-content { display:none; flex:1; overflow-y:auto; padding:35px; box-sizing:border-box; background:white; }
        .tab-content.active { display:block; }

        /* ESTILO CONTENIDO */
        .meta-box { border-bottom:2px solid #eee; margin-bottom:20px; padding-bottom:10px; }
        .meta-title { font-weight:900; font-size:22px; color:#000; margin:0; }
        .meta-info { font-size:12px; color:#666; margin-top:5px; text-transform:uppercase; }
        
        #chat-log { height:400px; overflow-y:auto; border:1px solid #eee; padding:15px; background:#f9f9f9; border-radius:8px; margin-bottom:10px; }
        .chat-row { display:flex; gap:10px; }
        .btn { padding:10px 15px; border:none; border-radius:4px; cursor:pointer; font-weight:bold; }
        .btn-zoom { background:#444; color:white; }
        .btn-dl { background:var(--banana); color:black; }
    </style>
</head>
<body>
    <div class="main">
        <div class="pdf-side">
            <div class="toolbar">
                <button class="btn btn-zoom" onclick="zoom(-0.2)">➖</button>
                <span id="z-txt">110%</span>
                <button class="btn btn-zoom" onclick="zoom(0.2)">➕</button>
                <span id="p-txt" style="font-size:12px; opacity:0.8; margin-left:10px;">Pág: 1 / -</span>
                <button class="btn btn-dl" onclick="download()">📥 DESCARGAR</button>
            </div>
            <div id="pdf-viewport" class="viewport" onscroll="updatePage()"></div>
        </div>
        <div class="data-side">
            <div class="tabs">
                <button class="tab-btn active" onclick="openTab(event, 'analisis')">Análisis Técnico</button>
                <button class="tab-btn" onclick="openTab(event, 'poster')">Póster UCI</button>
                <button class="tab-btn" onclick="openTab(event, 'chat')">Chat Experto</button>
            </div>
            <div id="analisis" class="tab-content active">
                <div class="meta-box" id="meta-out"></div>
                <div id="md-out" style="line-height:1.6;"></div>
            </div>
            <div id="poster" class="tab-content"><div id="html-out"></div></div>
            <div id="chat" class="tab-content">
                <div id="chat-log"></div>
                <div class="chat-row">
                    <input type="text" id="c-in" style="flex:1; padding:12px; border:1px solid #ddd; border-radius:5px;" placeholder="Duda técnica...">
                    <button onclick="ask()" style="padding:12px; background:black; color:white; border-radius:5px; cursor:pointer;">PREGUNTAR</button>
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
            document.getElementById('meta-out').innerHTML = `<h1 class="meta-title">${G.titulo}</h1><div class="meta-info">${G.autor} | ${G.revista} | ${G.fecha}</div>`;
            document.getElementById('md-out').innerHTML = marked.parse(G.analisis);
            document.getElementById('html-out').innerHTML = G.infografia;
            initPDF(PDF_B64);
        };

        async function initPDF(data) {
            const loadingTask = pdfjsLib.getDocument({data: atob(data)});
            pdfDoc = await loadingTask.promise;
            document.getElementById('p-txt').innerText = `Pág: 1 / ${pdfDoc.numPages}`;
            draw();
        }

        async function draw() {
            const view = document.getElementById('pdf-viewport'); view.innerHTML = "";
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
            for(let i=0; i<cans.length; i++) {
                if(cans[i].getBoundingClientRect().top >= 0) {
                    document.getElementById('p-txt').innerText = `Pág: ${i+1} / ${pdfDoc.numPages}`;
                    break;
                }
            }
        }

        function download() {
            const a = document.createElement('a'); a.href = "data:application/pdf;base64," + PDF_B64;
            a.download = G.titulo.replace(/\\s+/g, '_') + ".pdf"; a.click();
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
                const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/${MODEL}:generateContent?key=${API_KEY}`, {
                    method:'POST', headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({contents:[{parts:[{text: "Responde de forma técnica sobre el PDF: " + txt},{inline_data:{mime_type:"application/pdf", data:PDF_B64}}]}]})
                });
                const d = await r.json();
                const res = d.candidates[0].content.parts[0].text;
                log.innerHTML += `<div style="color:#2c3e50; border-left:3px solid var(--banana); padding-left:10px; margin-bottom:20px;"><b>IA:</b> ${marked.parse(res)}</div>`;
                log.scrollTop = log.scrollHeight;
            } catch(e) { log.innerHTML += "<div>Error de conexión.</div>"; }
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
    st.header("⚙️ Gestión Técnica de GPC")
    file = st.file_uploader("Subir Guía (PDF)", type="pdf")
    
    if file and st.button("🚀 INICIAR PROCESAMIENTO"):
        with st.spinner(f"Usando {active_model_name}..."):
            pdf_bytes = file.read()
            p_full = """Analiza este PDF en ESPAÑOL. 
            Extrae estrictamente: TITULO, AUTOR, REVISTA, FECHA. 
            Luego realiza un ANÁLISIS TÉCNICO: 
            1. METODOLOGÍA. 
            2. ANÁLISIS DELTA (Cambios clave). 
            3. BEDSIDE GUIDE (Protocolos). 
            4. FARMACOLOGÍA Y DOSIS. 
            5. PUNTOS CLAVE PARA RESIDENTES. 
            No uses lenguaje informal ni saludos."""
            
            p_html = "Genera un DIV HTML para un póster médico técnico. Blanco/Negro/Amarillo UCI."
            
            try:
                res_ia = model_ia.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p_full]).text
                res_html = model_ia.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p_html]).text
                
                # Extracción de metadatos
                t = re.search(r"TITULO:\s*(.*)", res_ia).group(1) if "TITULO:" in res_ia else file.name
                a = re.search(r"AUTOR:\s*(.*)", res_ia).group(1) if "AUTOR:" in res_ia else "Sociedad Médica"
                r = re.search(r"REVISTA:\s*(.*)", res_ia).group(1) if "REVISTA:" in res_ia else "Publicación Oficial"
                f = re.search(r"FECHA:\s*(.*)", res_ia).group(1) if "FECHA:" in res_ia else "2024"

                with get_db() as conn:
                    conn.execute('INSERT INTO guias (titulo, autor, revista, fecha_pub, pdf_blob, analisis_md, infografia_html) VALUES (?,?,?,?,?,?,?)',
                                 (t, a, r, f, pdf_bytes, res_ia, res_html.replace("```html", "").replace("```", "")))
                st.success("✅ Guía integrada.")
                st.rerun()
            except Exception as e:
                st.error(f"Error en el análisis: {e}")

elif 'active_id' in st.session_state:
    with get_db() as conn:
        g = conn.execute('SELECT * FROM guias WHERE id = ?', (st.session_state['active_id'],)).fetchone()
    
    if g:
        pdf_b64 = base64.b64encode(g['pdf_blob']).decode('utf-8')
        g_json = {
            "titulo": g['titulo'], "autor": g['autor'], "revista": g['revista'], 
            "fecha": g['fecha_pub'], "analisis": g['analisis_md'], "infografia": g['infografia_html']
        }
        
        render = html_template.replace("__API_KEY__", st.secrets["GEMINI_API_KEY"])
        render = render.replace("__MODEL__", active_model_name)
        render = render.replace("__PDF_B64__", pdf_b64)
        render = render.replace("__GUIA_JSON__", json.dumps(g_json))
        
        components.html(render, height=1200, scrolling=False)
else:
    st.title("Handover Médico NanoBanana")
    st.info("👈 Selecciona una guía técnica del panel lateral.")
