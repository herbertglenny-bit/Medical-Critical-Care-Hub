import streamlit as st
import streamlit.components.v1 as components

# Configuración: Layout Wide
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
    <title>Estación Médica V34 (Chat Fix)</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    </script>
    
    <style>
        /* --- GLOBAL --- */
        body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; font-family: 'Segoe UI', Roboto, sans-serif; background: #202124; }
        .main-container { display: flex; width: 100vw; height: 100vh; }
        
        /* --- VISOR PDF --- */
        .pdf-section { width: 50%; height: 100%; display: flex; flex-direction: column; border-right: 1px solid #444; background: #525659; }
        .pdf-toolbar { height: 50px; background: #323639; display: flex; align-items: center; justify-content: center; gap: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); z-index: 10; flex-shrink: 0; }
        .pdf-scroll-container { flex: 1; overflow: auto; padding: 40px; background: #525659; text-align: center; display: block; }
        .pdf-page-canvas { display: inline-block; box-shadow: 0 4px 15px rgba(0,0,0,0.6); margin-bottom: 20px; vertical-align: top; background: white; }

        /* --- PANELES IA --- */
        .right-panel { width: 50%; height: 100%; display: flex; flex-direction: column; background: #f0f2f5; }
        .tabs-header { height: 50px; background: #fff; border-bottom: 1px solid #ddd; display: flex; flex-shrink: 0; z-index: 5; }
        .tab-btn { flex: 1; border: none; background: transparent; cursor: pointer; font-weight: 600; color: #5f6368; font-size: 14px; border-bottom: 3px solid transparent; }
        .tab-btn.active { color: #1a73e8; border-bottom: 3px solid #1a73e8; background: #e8f0fe; }
        
        .content-area { flex: 1; overflow: auto; position: relative; display: flex; flex-direction: column; }
        .tab-content { display: none; width: 100%; }
        .tab-content.active { display: block; }

        /* --- MARKDOWN --- */
        .markdown-wrapper { padding: 40px; max-width: 900px; margin: auto; background: white; min-height: 100%; }
        .markdown-body { font-size: 16px; line-height: 1.7; color: #2c3e50; }
        .markdown-body h1 { color: #1565c0; border-bottom: 2px solid #eee; margin-top: 0; }
        .markdown-body h2 { color: #2c3e50; margin-top: 30px; border-left: 4px solid #1565c0; padding-left: 10px; }

        /* --- INFOGRAFÍA --- */
        #infografia-wrapper { padding: 50px; text-align: center; min-height: 100%; background: #dce1e6; display: block; }
        #infografia-visual-container { width: 900px; margin: 0 auto; background: white; box-shadow: 0 15px 50px rgba(0,0,0,0.2); font-family: 'Roboto', sans-serif; color: #333; text-align: left; overflow: visible; display: inline-block; }

        /* Estilos Póster */
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

        /* UI ELEMENTS */
        button { cursor: pointer; padding: 8px 16px; border-radius: 4px; border: none; font-weight: 600; font-size: 13px; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
        .btn-control { background: #fff; color: #333; }
        .btn-primary { background: #0d47a1; color: white; margin-left: auto; display: none; }
        .btn-pdf { background: #c5221f; color: white; text-decoration: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; display: none; }

        /* CHAT */
        #chat-history { padding: 20px; height: calc(100% - 70px); overflow-y: auto; }
        .chat-input-box { padding: 15px; border-top: 1px solid #eee; display: flex; gap: 10px; background: #fff; }
        .msg { padding: 12px 16px; border-radius: 12px; margin-bottom: 12px; font-size: 14px; max-width: 85%; }
        .msg.user { background: #e3f2fd; color: #1565c0; align-self: flex-end; }
        .msg.ai { background: #fff; border: 1px solid #eee; align-self: flex-start; }
        .msg.loading { color: #888; font-style: italic; }
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
                <div style="font-size:50px; margin-bottom:15px;">📁</div>
                <div style="font-weight:bold; font-size:18px;">ARRASTRA TU GUÍA CLÍNICA AQUÍ</div>
                <div style="font-size:13px; margin-top:5px; opacity:0.7;">Análisis Técnico + Infografía PRO</div>
            </div>
            <div id="pdf-container" class="pdf-scroll-container" style="display:none;"></div>
        </div>

        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="abrirPestana('tab-analisis')">📝 Análisis</button>
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">🎨 Infografía Visual</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">💬 Chat</button>
                <button id="btn-save-img" class="btn-primary" onclick="descargarPoster()">📸 Descargar Imagen</button>
            </div>
            
            <div class="content-area">
                <div id="tab-analisis" class="tab-content active">
                    <div class="markdown-wrapper">
                        <div id="analisis-content" class="markdown-body">
                            <div style="text-align:center; margin-top:100px; color:#bbb;">Esperando documento...</div>
                        </div>
                    </div>
                </div>

                <div id="tab-infografia" class="tab-content">
                    <div id="infografia-wrapper">
                        <div id="infografia-visual-container">
                            <div style="padding:100px; text-align:center; color:#bbb;">
                                El póster se generará aquí automáticamente.
                            </div>
                        </div>
                    </div>
                </div>

                <div id="tab-chat" class="tab-content" style="height:100%;">
                    <div style="display: flex; flex-direction: column; height: 100%;">
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

        const dropZone = document.getElementById('drop-zone');
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.style.background = "#444"; });
        dropZone.addEventListener('dragleave', () => { dropZone.style.background = "transparent"; });
        
        dropZone.addEventListener('drop', async (e) => {
            e.preventDefault();
            const file = e.dataTransfer.files[0];
            if(file && file.type === "application/pdf") {
                dropZone.style.display = "none";
                document.getElementById('pdf-container').style.display = "block"; 
                document.getElementById('analisis-content').innerHTML = "<div style='text-align:center; margin-top:50px;'>🧠 <b>Diseccionando Guía...</b></div>";
                document.getElementById('infografia-visual-container').innerHTML = "<div style='padding:80px; text-align:center; color:#999;'>🎨 <b>Diseñando Infografía...</b></div>";
                const fileURL = URL.createObjectURL(file);
                document.getElementById('btn-download').href = fileURL;
                document.getElementById('btn-download').style.display = 'inline-block';
                cargarPDF(fileURL);
                const reader = new FileReader();
                reader.onload = async () => { globalPdfBase64 = reader.result.split(',')[1]; iniciarProcesamientoParalelo(); };
                reader.readAsDataURL(file);
            }
        });

        async function cargarPDF(url) { pdfDoc = await pdfjsLib.getDocument(url).promise; renderizarTodo(); }
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

        function iniciarProcesamientoParalelo() { procesarAnalisisTexto(); procesarInfografiaVisual(); }

        // --- HILO 1: ANÁLISIS ---
        async function procesarAnalisisTexto() {
            const prompt = `
            ERES UN MOTOR DE DATOS MÉDICOS. PROHIBIDO SALUDAR. EMPIEZA DIRECTO CON EL TÍTULO (# Título).
            Analiza la Guía: 1. Definiciones 2. Algoritmo Agudo 3. Soporte Vital 4. Semáforo Evidencia 5. Poblaciones.
            `;
            const res = await llamarIA(prompt);
            if(res) document.getElementById('analisis-content').innerHTML = marked.parse(limpiarTexto(res));
        }

        // --- HILO 2: INFOGRAFÍA ---
        async function procesarInfografiaVisual() {
            const promptPoster = `
            Genera HTML para PÓSTER MÉDICO (Diseño V31). SOLO HTML.
            <div class="poster-header"><h1 class="poster-title">TITULO</h1><div class="poster-meta">META</div></div>
            <div class="poster-body">
                <div class="section-title">SEMÁFORO</div>
                <div class="traffic-container">
                    <div class="traffic-col tc-stop"><span class="traffic-icon">⛔</span><div class="traffic-title">STOP</div><ul><li>...</li></ul></div>
                    <div class="traffic-col tc-wait"><span class="traffic-icon">⚠️</span><div class="traffic-title">PRECAUCIÓN</div><ul><li>...</li></ul></div>
                    <div class="traffic-col tc-go"><span class="traffic-icon">✅</span><div class="traffic-title">GO</div><ul><li>...</li></ul></div>
                </div>
                <div class="section-title">CIFRAS CLAVE</div>
                <div class="metrics-grid">
                    <div class="metric-card"><span class="metric-val">X</span><span class="metric-lbl">L1</span></div>
                    <div class="metric-card"><span class="metric-val">Y</span><span class="metric-lbl">L2</span></div>
                    <div class="metric-card"><span class="metric-val">Z</span><span class="metric-lbl">L3</span></div>
                </div>
                <div class="section-title">ALGORITMO</div><div id="mermaid-placeholder" class="poster-mermaid"></div>
            </div>
            <div class="poster-footer"><h3>TAKE HOME</h3><div class="footer-list"><div class="footer-item">M1</div></div></div>
            `;
            
            const html = await llamarIA(promptPoster);
            if(html) {
                document.getElementById('infografia-visual-container').innerHTML = limpiarTexto(html);
                const target = document.getElementById('mermaid-placeholder');
                if(target) {
                    target.innerHTML = "Generando gráfico...";
                    const mer = await llamarIA(`Crea 'mermaid graph TD' SIMPLE (max 8 nodos). TEXTOS ENTRE COMILLAS DOBLES. Solo código.`);
                    if(mer) {
                        target.innerHTML = `<div class="mermaid">${limpiarMermaid(mer)}</div>`;
                        try { mermaid.run(); } catch(e){}
                    }
                }
                if(document.getElementById('tab-infografia').classList.contains('active')) {
                    document.getElementById('btn-save-img').style.display = 'block';
                }
            }
        }

        // --- MOTOR IA ROBUSTO (REINTENTOS) ---
        async function llamarIA(p, retries = 2) {
            try {
                if (WORKING_MODEL) return await fetchGemini(p, WORKING_MODEL);
                for (let m of MODEL_CANDIDATES) {
                    const r = await fetchGemini(p, m);
                    if (r && !r.startsWith("Error")) { WORKING_MODEL = m; return r; }
                }
                throw new Error("Todos los modelos fallaron");
            } catch (e) {
                if(retries > 0) {
                    console.warn("Reintentando IA...");
                    await new Promise(r => setTimeout(r, 2000)); // Esperar 2s
                    return llamarIA(p, retries - 1);
                }
                return "Error: Servicio saturado. Intente en unos segundos.";
            }
        }

        async function fetchGemini(prompt, modelo) {
            if(!globalPdfBase64) return null;
            try {
                const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${modelo}:generateContent?key=${API_KEY}`, {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ contents: [{ parts: [{ text: prompt }, { inline_data: { mime_type: "application/pdf", data: globalPdfBase64 } }] }] })
                });
                if (r.status === 429) return "Error 429"; // Rate Limit Hit
                const d = await r.json();
                if(d.error) return "Error: " + d.error.message;
                return d.candidates[0].content.parts[0].text;
            } catch(e) { return "Error Red"; }
        }

        function limpiarTexto(t) { return t.replace(/```html|```/gi, "").trim(); }
        function limpiarMermaid(t) { let l = t.replace(/```mermaid|```/gi, ""); const i = l.indexOf("graph TD"); if(i !== -1) l = l.substring(i); return l.trim(); }

        // --- CHAT FIX ---
        async function enviarMensaje() {
            const i = document.getElementById('user-input'), h = document.getElementById('chat-history');
            const t = i.value; if(!t) return;
            
            // UI Update Usuario
            h.innerHTML += `<div class="msg user">${t}</div>`; 
            i.value=""; h.scrollTop = h.scrollHeight;
            
            // Loading Indicator
            const loadingId = "loading-" + Date.now();
            h.innerHTML += `<div id="${loadingId}" class="msg ai loading">Escribiendo...</div>`;
            h.scrollTop = h.scrollHeight;

            // Llamada IA
            const r = await llamarIA(`Actúa como experto médico. Responde brevemente: ${t}`);
            
            // Remove Loading
            document.getElementById(loadingId).remove();
            
            // UI Update IA
            const content = r && !r.startsWith("Error") ? marked.parse(limpiarTexto(r)) : `<span style="color:red">${r}</span>`;
            h.innerHTML += `<div class="msg ai">${content}</div>`;
            h.scrollTop = h.scrollHeight;
        }

        function descargarPoster() {
            const el = document.getElementById('infografia-visual-container');
            html2canvas(el, { scale: 3, windowWidth: el.scrollWidth, windowHeight: el.scrollHeight, backgroundColor: "#ffffff" }).then(canvas => {
                const a = document.createElement('a'); a.download = 'Infografia_Medica_Pro.png'; a.href = canvas.toDataURL('image/png'); a.click();
            });
        }
    </script>
</body>
</html>
"""

final_html = html_template.replace("__API_KEY_PLACEHOLDER__", API_KEY)
components.html(final_html, height=1000, scrolling=True)
