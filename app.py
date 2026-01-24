import streamlit as st
import streamlit.components.v1 as components

# Configuración: Layout Wide y Sidebar colapsado por defecto
st.set_page_config(page_title="Estación Médica IA", layout="wide", initial_sidebar_state="collapsed")

# --- SEGURIDAD ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except (FileNotFoundError, KeyError):
    st.error("⚠️ Error: Falta 'GEMINI_API_KEY' en Secrets.")
    st.stop()
# -----------------

html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Estación Médica V28</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    </script>
    
    <style>
        /* --- LAYOUT MASTER (FULL SCREEN) --- */
        body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #202124; }
        
        .main-container { display: flex; width: 100vw; height: 100vh; }
        
        /* --- IZQUIERDA: VISOR PDF --- */
        .pdf-section { width: 50%; height: 100%; display: flex; flex-direction: column; border-right: 1px solid #444; background: #525659; }
        
        .pdf-toolbar { 
            height: 50px; background: #323639; display: flex; align-items: center; justify-content: center; gap: 10px; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.2); z-index: 10;
        }
        
        /* Scroll container que permite X e Y */
        .pdf-scroll-container { 
            flex: 1; 
            overflow: auto; /* Scroll automático en ambas direcciones */
            padding: 20px; 
            display: flex; 
            flex-direction: column; 
            align-items: center; /* Centrado por defecto */
            background: #525659;
        }
        /* Cuando el zoom es grande, JS cambia align-items a flex-start para permitir scroll horizontal */

        .pdf-page-canvas { box-shadow: 0 4px 10px rgba(0,0,0,0.5); margin-bottom: 15px; flex-shrink: 0; }

        /* --- DERECHA: PANELES IA --- */
        .right-panel { width: 50%; height: 100%; display: flex; flex-direction: column; background: #f8f9fa; }
        
        .tabs-header { 
            height: 50px; background: #fff; border-bottom: 1px solid #ddd; display: flex; flex-shrink: 0; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); z-index: 5;
        }
        .tab-btn { 
            flex: 1; border: none; background: transparent; cursor: pointer; font-weight: 600; color: #5f6368; 
            font-size: 14px; transition: 0.2s; border-bottom: 3px solid transparent;
        }
        .tab-btn:hover { background: #f1f3f4; color: #1a73e8; }
        .tab-btn.active { color: #1a73e8; border-bottom: 3px solid #1a73e8; background: #e8f0fe; }
        
        /* Contenedor de contenido con scroll independiente */
        .content-area { 
            flex: 1; 
            overflow-y: auto; /* Solo scroll vertical aquí */
            overflow-x: hidden;
            position: relative; 
            background: #fff;
        }
        
        .tab-content { display: none; padding: 30px; max-width: 900px; margin: auto; }
        .tab-content.active { display: block; }

        /* --- ESTILOS ANÁLISIS (MARKDOWN) --- */
        .markdown-body { font-size: 16px; line-height: 1.7; color: #2c3e50; }
        .markdown-body h1 { color: #1565c0; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 0; }
        .markdown-body h2 { color: #2c3e50; margin-top: 30px; border-left: 4px solid #1565c0; padding-left: 10px; }
        .markdown-body strong { color: #c62828; }

        /* --- ESTILOS INFOGRAFÍA VISUAL (PÓSTER) --- */
        #infografia-wrapper {
            display: flex; justify-content: center; background: #e9ecef; padding: 40px; border-radius: 8px;
        }
        #infografia-visual-container {
            width: 800px; /* Ancho fijo A4 para exportación */
            background: white;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            font-family: 'Roboto', sans-serif;
            color: #333;
            overflow: hidden;
        }

        /* Diseño Header */
        .poster-header { background: #01579b; color: white; padding: 40px; text-align: center; border-bottom: 5px solid #ffab00; }
        .poster-title { font-size: 36px; font-weight: 900; margin: 0; line-height: 1.1; text-transform: uppercase; }
        .poster-meta { margin-top: 15px; font-size: 14px; opacity: 0.9; font-weight: 300; letter-spacing: 1px; }

        /* Diseño Cuerpo */
        .poster-body { padding: 40px; background: #fff; }
        
        /* Grid Semáforo */
        .traffic-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 40px; }
        .t-card { padding: 20px; border-radius: 8px; border: 1px solid #eee; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .t-card h3 { margin: 0 0 10px 0; font-size: 16px; font-weight: 900; text-transform: uppercase; display: flex; align-items: center; gap: 8px; }
        .t-card ul { padding-left: 15px; margin: 0; font-size: 13px; color: #444; }
        .t-card li { margin-bottom: 5px; }

        .tc-stop { background: #ffebee; border-top: 4px solid #d32f2f; } .tc-stop h3 { color: #b71c1c; }
        .tc-wait { background: #fff8e1; border-top: 4px solid #ff8f00; } .tc-wait h3 { color: #ff6f00; }
        .tc-go { background: #e8f5e9; border-top: 4px solid #2e7d32; } .tc-go h3 { color: #1b5e20; }

        /* Grid Datos (Big Numbers) */
        .big-nums { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 40px; }
        .bn-card { background: #f5f5f5; padding: 20px; border-radius: 8px; border-left: 5px solid #0277bd; text-align: center; }
        .bn-val { display: block; font-size: 32px; font-weight: 900; color: #0277bd; }
        .bn-lbl { font-size: 12px; font-weight: 700; color: #666; text-transform: uppercase; margin-top: 5px; }

        /* Footer */
        .poster-footer { background: #263238; color: white; padding: 30px; text-align: center; }
        .poster-footer h3 { color: #80cbc4; margin: 0 0 15px 0; font-size: 16px; font-weight: 900; text-transform: uppercase; letter-spacing: 1px; }
        .poster-footer ul { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }
        .poster-footer li { background: rgba(255,255,255,0.1); padding: 8px 15px; border-radius: 20px; font-size: 13px; }

        /* Diagrama Mermaid */
        .poster-mermaid { margin-top: 40px; padding-top: 20px; border-top: 2px dashed #eee; text-align: center; }
        .poster-mermaid h4 { color: #999; text-transform: uppercase; letter-spacing: 2px; font-size: 12px; margin-bottom: 20px; }

        /* --- BOTONES --- */
        button { cursor: pointer; padding: 8px 16px; border-radius: 4px; border: none; font-weight: 600; font-size: 13px; box-shadow: 0 1px 3px rgba(0,0,0,0.2); transition: 0.2s; }
        button:hover { transform: translateY(-1px); }
        .btn-control { background: #fff; color: #333; }
        .btn-primary { background: #1a73e8; color: white; margin-left: auto; display: none; } /* Botón descarga a la derecha */
        .btn-pdf { background: #d32f2f; color: white; text-decoration: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; display: none; }

        /* --- CHAT --- */
        .chat-container { display: flex; flex-direction: column; height: 100%; padding: 0; }
        #chat-history { flex: 1; overflow-y: auto; padding: 20px; }
        .chat-input-box { padding: 15px; border-top: 1px solid #eee; display: flex; gap: 10px; background: #fff; }
        .msg { padding: 12px 16px; border-radius: 12px; margin-bottom: 12px; max-width: 85%; font-size: 14px; line-height: 1.5; }
        .msg.user { background: #e3f2fd; color: #1565c0; align-self: flex-end; }
        .msg.ai { background: #f1f1f1; color: #333; align-self: flex-start; }
    </style>
</head>
<body>

    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button class="btn-control" onclick="ajustarZoom(-0.2)">➖</button>
                <span id="zoom-level" style="color:white; font-size:12px; margin:0 10px;">100%</span>
                <button class="btn-control" onclick="ajustarZoom(0.2)">➕</button>
                <a id="btn-download" class="btn-pdf">⬇️ PDF</a>
            </div>
            
            <div id="drop-zone" style="flex:1; display:flex; flex-direction:column; justify-content:center; align-items:center; color:#ccc; cursor:pointer;">
                <div style="font-size:48px; margin-bottom:15px;">📁</div>
                <div style="font-weight:bold; font-size:18px;">ARRASTRA TU GUÍA CLÍNICA AQUÍ</div>
                <div style="font-size:13px; margin-top:5px; opacity:0.7;">Análisis Técnico + Infografía Visual</div>
            </div>
            
            <div id="pdf-container" class="pdf-scroll-container" style="display:none;"></div>
        </div>

        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="abrirPestana('tab-analisis')">📝 Análisis</button>
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">🎨 Infografía Visual</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">💬 Chat</button>
                <button id="btn-save-img" class="btn-primary" onclick="descargarPoster()">📸 Guardar Imagen</button>
            </div>
            
            <div class="content-area">
                <div id="tab-analisis" class="tab-content active">
                    <div id="analisis-content" class="markdown-body">
                        <div style="text-align:center; margin-top:100px; color:#bbb;">
                            Esperando documento para análisis...
                        </div>
                    </div>
                </div>

                <div id="tab-infografia" class="tab-content">
                    <div id="infografia-wrapper">
                        <div id="infografia-visual-container">
                            <div style="padding:80px; text-align:center; color:#bbb;">
                                La infografía se generará aquí.
                            </div>
                        </div>
                    </div>
                </div>

                <div id="tab-chat" class="tab-content" style="height:100%; padding:0; max-width:none;">
                    <div class="chat-container">
                        <div id="chat-history"></div>
                        <div class="chat-input-box">
                            <input type="text" id="user-input" placeholder="Pregunta técnica..." style="flex:1; padding:10px; border:1px solid #ddd; border-radius:20px; outline:none;" onkeypress="if(event.key==='Enter') enviarMensaje()">
                            <button onclick="enviarMensaje()" style="background:#1565c0; color:white; padding:8px 20px; border-radius:20px;">Enviar</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_KEY = "__API_KEY_PLACEHOLDER__"; 
        const MODEL_CANDIDATES = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-pro"];
        let WORKING_MODEL = null;
        let pdfDoc = null, scale = 1.0, rotation = 0, globalPdfBase64 = null;
        mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' });

        // --- UI LOGIC ---
        function abrirPestana(id) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            
            const btn = document.getElementById('btn-save-img');
            const hasContent = document.querySelector('.poster-title');
            if(id === 'tab-infografia' && hasContent) btn.style.display = 'block';
            else btn.style.display = 'none';

            if(id.includes('analisis')) document.querySelectorAll('.tab-btn')[0].classList.add('active');
            if(id.includes('infografia')) document.querySelectorAll('.tab-btn')[1].classList.add('active');
            if(id.includes('chat')) document.querySelectorAll('.tab-btn')[2].classList.add('active');
        }

        // --- PDF LOGIC (SCROLL FIX) ---
        const dropZone = document.getElementById('drop-zone');
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.style.background = "#444"; });
        dropZone.addEventListener('dragleave', () => { dropZone.style.background = "transparent"; });
        
        dropZone.addEventListener('drop', async (e) => {
            e.preventDefault();
            const file = e.dataTransfer.files[0];
            if(file && file.type === "application/pdf") {
                dropZone.style.display = "none";
                document.getElementById('pdf-container').style.display = "flex";
                
                // Estados de carga
                document.getElementById('analisis-content').innerHTML = "<div style='text-align:center; margin-top:50px;'>🧠 <b>Diseccionando Guía...</b></div>";
                document.getElementById('infografia-visual-container').innerHTML = "<div style='padding:80px; text-align:center; color:#999;'>🎨 <b>Diseñando Infografía...</b></div>";

                const fileURL = URL.createObjectURL(file);
                document.getElementById('btn-download').href = fileURL;
                document.getElementById('btn-download').style.display = 'inline-block';
                
                cargarPDF(fileURL);
                const reader = new FileReader();
                reader.onload = async () => {
                    globalPdfBase64 = reader.result.split(',')[1];
                    iniciarProcesamientoParalelo(); 
                };
                reader.readAsDataURL(file);
            }
        });

        async function cargarPDF(url) { pdfDoc = await pdfjsLib.getDocument(url).promise; renderizarTodo(); }
        async function renderizarTodo() {
            const container = document.getElementById('pdf-container'); container.innerHTML = "";
            document.getElementById('zoom-level').innerText = Math.round(scale * 100) + "%";
            
            // FIX: Alineación para permitir scroll horizontal si es más ancho
            container.style.alignItems = scale > 1.2 ? "flex-start" : "center";

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

        // --- PARALLEL PROCESSING ---
        function iniciarProcesamientoParalelo() {
            procesarAnalisisTexto();
            procesarInfografiaVisual();
        }

        async function procesarAnalisisTexto() {
            // PROMPT ESTRICTO: Solo Título y Contenido. Sin charlas.
            const prompt = `
            Actúa como un Sistema Experto en Medicina Intensiva.
            Analiza la Guía Clínica adjunta.
            
            INSTRUCCIÓN DE FORMATO:
            1. Empieza DIRECTAMENTE con el Título del Documento como H1 (# Título).
            2. NO escribas frases introductorias como "Aquí tienes el análisis" o "Como sistema experto".
            3. Estructura:
               - Definiciones y Criterios
               - Algoritmo de Manejo (Targets, Dosis)
               - Soporte Vital
               - Semáforo de Evidencia
               - Poblaciones Especiales
            `;
            const res = await llamarIA(prompt);
            if(res) document.getElementById('analisis-content').innerHTML = marked.parse(limpiarTexto(res));
        }

        async function procesarInfografiaVisual() {
            // PROMPT VISUAL: Tarjetas y colores
            const promptPoster = `
            Actúa como Diseñador Gráfico Médico. Genera HTML para un PÓSTER VISUAL atractivo.
            REGLAS: SOLO HTML. Estructura exacta:

            <div class="poster-header">
                <h1 class="poster-title">TITULO DEL GUIDELINE</h1>
                <div class="poster-meta">AÑO • SOCIEDAD • TEMA</div>
            </div>

            <div class="poster-body">
                <div class="traffic-grid">
                    <div class="t-card tc-stop">
                        <h3>⛔ STOP (No hacer)</h3>
                        <ul><li>...</li></ul>
                    </div>
                    <div class="t-card tc-wait">
                        <h3>⚠️ PRECAUCIÓN</h3>
                        <ul><li>...</li></ul>
                    </div>
                    <div class="t-card tc-go">
                        <h3>✅ GO (Estándar)</h3>
                        <ul><li>...</li></ul>
                    </div>
                </div>

                <div class="big-nums">
                    <div class="bn-card">
                        <span class="bn-val">X</span>
                        <span class="bn-lbl">DATO CLAVE 1</span>
                    </div>
                    <div class="bn-card">
                        <span class="bn-val">Y</span>
                        <span class="bn-lbl">DATO CLAVE 2</span>
                    </div>
                </div>

                <div id="mermaid-placeholder" class="poster-mermaid"></div>
            </div>

            <div class="poster-footer">
                <h3>TAKE HOME MESSAGES</h3>
                <ul><li>Mensaje 1</li><li>Mensaje 2</li></ul>
            </div>
            `;
            
            const html = await llamarIA(promptPoster);
            if(html) {
                document.getElementById('infografia-visual-container').innerHTML = limpiarTexto(html);
                
                // Sub-proceso Gráfico
                const target = document.getElementById('mermaid-placeholder');
                if(target) {
                    target.innerHTML = "<h4>Algoritmo de Flujo</h4><div>Generando gráfico...</div>";
                    const promptMermaid = `Crea diagrama 'mermaid graph TD' SIMPLE (max 8 nodos). IDs cortos. TEXTOS ENTRE COMILLAS DOBLES. Solo código.`;
                    const mer = await llamarIA(promptMermaid);
                    if(mer) {
                        target.innerHTML = `<h4>Algoritmo de Flujo</h4><div class="mermaid">${limpiarMermaid(mer)}</div>`;
                        try { mermaid.run(); } catch(e){}
                    }
                }
                
                if(document.getElementById('tab-infografia').classList.contains('active')) {
                    document.getElementById('btn-save-img').style.display = 'block';
                }
            }
        }

        async function llamarIA(prompt) {
            if (WORKING_MODEL) return await fetchGemini(prompt, WORKING_MODEL);
            for (let modelo of MODEL_CANDIDATES) {
                const res = await fetchGemini(prompt, modelo);
                if (res && !res.startsWith("Error")) { WORKING_MODEL = modelo; return res; }
            }
            return null;
        }

        async function fetchGemini(prompt, modelo) {
            if(!globalPdfBase64) return null;
            try {
                const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${modelo}:generateContent?key=${API_KEY}`, {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ contents: [{ parts: [{ text: prompt }, { inline_data: { mime_type: "application/pdf", data: globalPdfBase64 } }] }] })
                });
                const d = await r.json();
                if(d.error) return "Error";
                return d.candidates[0].content.parts[0].text;
            } catch(e) { return "Error"; }
        }

        function limpiarTexto(t) { return t.replace(/```html|```/gi, "").trim(); }
        function limpiarMermaid(t) { let l = t.replace(/```mermaid|```/gi, ""); const i = l.indexOf("graph TD"); if(i !== -1) l = l.substring(i); return l.trim(); }

        async function enviarMensaje() {
            const i = document.getElementById('user-input');
            const h = document.getElementById('chat-history');
            const t = i.value; if(!t) return;
            h.innerHTML += `<div class="msg user">${t}</div>`; i.value=""; h.scrollTop = h.scrollHeight;
            const res = await llamarIA(`Respuesta técnica breve: ${t}`);
            h.innerHTML += `<div class="msg ai">${res ? marked.parse(limpiarTexto(res)) : "Error"}</div>`;
            h.scrollTop = h.scrollHeight;
        }

        function descargarPoster() {
            const el = document.getElementById('infografia-visual-container');
            html2canvas(el, { scale: 2.5, backgroundColor: "#ffffff" }).then(canvas => {
                const a = document.createElement('a');
                a.download = 'Infografia_Medica.png';
                a.href = canvas.toDataURL('image/png');
                a.click();
            });
        }
    </script>
</body>
</html>
"""

final_html = html_template.replace("__API_KEY_PLACEHOLDER__", API_KEY)
components.html(final_html, height=1000, scrolling=True)
