import streamlit as st
import streamlit.components.v1 as components

# Configuración de página
st.set_page_config(page_title="Estación Médica IA", layout="wide", initial_sidebar_state="collapsed")

# --- SEGURIDAD ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except (FileNotFoundError, KeyError):
    st.error("⚠️ Error Crítico: No se encuentra 'GEMINI_API_KEY' en los Secrets.")
    st.stop()
# -----------------

html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Estación Médica V27 (Turbo)</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    </script>
    
    <style>
        /* --- LAYOUT GLOBAL --- */
        body { margin: 0; padding: 0; background-color: #f4f6f9; height: 100vh; display: flex; flex-direction: column; overflow: hidden; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        
        .main-container { display: flex; width: 100vw; height: 100vh; }
        
        /* IZQUIERDA: VISOR PDF */
        .pdf-section { width: 50%; min-width: 50%; border-right: 1px solid #ddd; background: #525659; display: flex; flex-direction: column; }
        .pdf-toolbar { background: #333; padding: 10px; display: flex; gap: 10px; justify-content: center; align-items: center; color: white; }
        .pdf-scroll-container { flex: 1; overflow: auto; display: flex; flex-direction: column; align-items: center; padding: 20px; }
        .pdf-page-canvas { box-shadow: 0 4px 10px rgba(0,0,0,0.5); margin-bottom: 15px; }

        /* DERECHA: PANELES IA */
        .right-panel { width: 50%; min-width: 50%; display: flex; flex-direction: column; background: #fff; }
        
        /* PESTAÑAS */
        .tabs-header { display: flex; background: #f8f9fa; border-bottom: 1px solid #ddd; }
        .tab-btn { flex: 1; padding: 15px; border: none; background: transparent; cursor: pointer; font-weight: 600; color: #5f6368; border-bottom: 3px solid transparent; transition: 0.2s; font-size: 14px; }
        .tab-btn:hover { color: #1a73e8; background: #f1f3f4; }
        .tab-btn.active { color: #1a73e8; border-bottom: 3px solid #1a73e8; background: white; }
        
        .tab-content { flex: 1; padding: 0; overflow-y: auto; display: none; background: #fff; position: relative; }
        .tab-content.active { display: block; }
        .content-padding { padding: 30px; max-width: 900px; margin: auto; }

        /* --- ESTILOS DEL ANÁLISIS (MARKDOWN) --- */
        .markdown-body { font-size: 16px; line-height: 1.7; color: #2c3e50; }
        .markdown-body h1 { color: #1a73e8; border-bottom: 2px solid #eee; padding-bottom: 10px; font-size: 24px; }
        .markdown-body h2 { color: #2c3e50; margin-top: 30px; border-left: 4px solid #1a73e8; padding-left: 10px; font-size: 20px; }
        .markdown-body strong { color: #d32f2f; background: rgba(211, 47, 47, 0.05); padding: 0 4px; border-radius: 3px; }

        /* --- ESTILOS DE LA INFOGRAFÍA VISUAL (PÓSTER) --- */
        #infografia-wrapper { background: #e9ecef; padding: 40px; display: flex; justify-content: center; min-height: 100%; }

        #infografia-visual-container {
            width: 800px; /* Ancho fijo A4 */
            background: white;
            box-shadow: 0 20px 50px rgba(0,0,0,0.15);
            font-family: 'Roboto', 'Segoe UI', sans-serif;
            color: #333;
            overflow: hidden;
            border-radius: 4px;
        }

        .poster-header { background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); color: white; padding: 40px; text-align: center; }
        .poster-title { font-size: 32px; font-weight: 900; margin: 0; line-height: 1.1; letter-spacing: -0.5px; }
        .poster-meta { margin-top: 15px; font-size: 14px; opacity: 0.8; font-weight: 300; text-transform: uppercase; letter-spacing: 1px; }

        .poster-body { padding: 40px; }

        .traffic-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 40px; }
        .t-card { background: #f8f9fa; border-radius: 12px; padding: 20px; border: 1px solid #eee; }
        .t-card h3 { margin: 0 0 15px 0; font-size: 14px; font-weight: 900; text-transform: uppercase; }
        .tc-stop { border-top: 6px solid #e53935; } .tc-stop h3 { color: #c62828; }
        .tc-wait { border-top: 6px solid #fbc02d; } .tc-wait h3 { color: #f57f17; }
        .tc-go   { border-top: 6px solid #43a047; } .tc-go h3   { color: #2e7d32; }

        .big-nums { display: flex; gap: 20px; justify-content: center; margin-bottom: 40px; background: #fff; padding: 20px 0; border-top: 1px dashed #ddd; border-bottom: 1px dashed #ddd; }
        .bn-item { text-align: center; flex: 1; border-right: 1px solid #eee; }
        .bn-item:last-child { border: none; }
        .bn-val { display: block; font-size: 36px; font-weight: 800; color: #2c5364; }
        .bn-lbl { font-size: 11px; text-transform: uppercase; color: #888; font-weight: 700; }

        .poster-footer { background: #f1f8e9; padding: 30px 40px; border-radius: 12px; border: 1px solid #dcedc8; }
        .poster-footer h3 { margin: 0 0 10px 0; color: #558b2f; font-size: 14px; text-transform: uppercase; font-weight: 800; }
        .poster-footer ul { margin: 0; padding-left: 20px; color: #33691e; font-size: 14px; }

        .poster-mermaid { margin-top: 40px; text-align: center; border-top: 2px dashed #eee; padding-top: 20px; }

        /* BOTONES */
        button { cursor: pointer; padding: 8px 16px; border-radius: 4px; border: none; font-weight: 600; font-size: 13px; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
        .btn-zoom { background: white; color: #333; }
        .btn-pdf { background: #e53935; color: white; text-decoration: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; display: none; }
        .btn-action { background: #00897b; color: white; display: none; margin-left: 10px; }
        .btn-action:hover { background: #00796b; }

        /* CHAT */
        #chat-history { padding: 20px; height: calc(100% - 70px); overflow-y: auto; }
        .msg { padding: 12px 16px; border-radius: 12px; margin-bottom: 12px; font-size: 14px; max-width: 85%; }
        .msg.user { background: #e3f2fd; color: #1565c0; align-self: flex-end; }
        .msg.ai { background: #f5f5f5; color: #333; border: 1px solid #eee; align-self: flex-start; }
    </style>
</head>
<body>

    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button class="btn-zoom" onclick="ajustarZoom(-0.2)">➖</button>
                <span id="zoom-level" style="color:white; font-size:12px; margin:0 10px;">100%</span>
                <button class="btn-zoom" onclick="ajustarZoom(0.2)">➕</button>
                <a id="btn-download" class="btn-pdf">⬇️ PDF</a>
            </div>
            
            <div id="drop-zone" style="flex:1; display:flex; flex-direction:column; justify-content:center; align-items:center; color:#ccc; cursor:pointer;">
                <div style="font-size:40px; margin-bottom:10px;">⚡</div>
                <div style="font-weight:bold;">ARRASTRA TU GUÍA CLÍNICA AQUÍ</div>
                <div style="font-size:12px; margin-top:5px;">Modo Turbo: Análisis + Infografía Simultáneos</div>
            </div>
            
            <div id="pdf-container" class="pdf-scroll-container" style="display:none;"></div>
        </div>

        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="abrirPestana('tab-analisis')">📝 Análisis</button>
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">🎨 Infografía Visual</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">💬 Chat</button>
                <button id="btn-save-img" class="btn-action" onclick="descargarPoster()">📸 Descargar</button>
            </div>
            
            <div id="tab-analisis" class="tab-content active">
                <div class="content-padding">
                    <div id="analisis-content" class="markdown-body">
                        <div style="text-align:center; margin-top:80px; color:#aaa;">Esperando archivo...</div>
                    </div>
                </div>
            </div>

            <div id="tab-infografia" class="tab-content">
                <div id="infografia-wrapper">
                    <div id="infografia-visual-container">
                        <div style="padding:60px; text-align:center; color:#999;">El póster aparecerá aquí.</div>
                    </div>
                </div>
            </div>

            <div id="tab-chat" class="tab-content">
                <div id="chat-history"></div>
                <div style="padding:10px; border-top:1px solid #eee; display:flex; gap:10px;">
                    <input type="text" id="user-input" placeholder="Pregunta..." style="flex:1; padding:10px; border:1px solid #ddd; border-radius:20px;" onkeypress="if(event.key==='Enter') enviarMensaje()">
                    <button onclick="enviarMensaje()" style="background:#1a73e8; color:white;">Enviar</button>
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

        // --- GESTIÓN UI ---
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

        // --- PDF LOGIC ---
        const dropZone = document.getElementById('drop-zone');
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.style.background = "#333"; });
        dropZone.addEventListener('dragleave', () => { dropZone.style.background = "transparent"; });
        
        dropZone.addEventListener('drop', async (e) => {
            e.preventDefault();
            const file = e.dataTransfer.files[0];
            if(file && file.type === "application/pdf") {
                dropZone.style.display = "none";
                document.getElementById('pdf-container').style.display = "flex";
                
                // INDICADORES DE CARGA SIMULTÁNEA
                document.getElementById('analisis-content').innerHTML = "<div style='text-align:center; margin-top:50px;'>🧠 <b>Analizando Texto...</b></div>";
                document.getElementById('infografia-visual-container').innerHTML = "<div style='padding:60px; text-align:center; color:#999;'>🎨 <b>Diseñando Póster...</b></div>";

                const fileURL = URL.createObjectURL(file);
                document.getElementById('btn-download').href = fileURL;
                document.getElementById('btn-download').style.display = 'inline-block';
                
                cargarPDF(fileURL);
                const reader = new FileReader();
                reader.onload = async () => {
                    globalPdfBase64 = reader.result.split(',')[1];
                    iniciarProcesamientoParalelo(); // <--- AQUÍ ESTÁ LA MAGIA
                };
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

        // --- PROCESAMIENTO PARALELO (TURBO) ---
        function iniciarProcesamientoParalelo() {
            // LANZAMOS LOS DOS PROCESOS A LA VEZ SIN ESPERARSE MUTUAMENTE
            procesarAnalisisTexto();
            procesarInfografiaVisual();
        }

        // HILO 1: ANÁLISIS DE TEXTO
        async function procesarAnalisisTexto() {
            const prompt = `
            Actúa como un Sistema Experto en Medicina Intensiva. 
            Realiza una disección técnica exhaustiva de la Guía de Práctica Clínica.
            ESTRUCTURA MARKDOWN:
            1. **Definiciones y Nuevos Criterios**
            2. **Algoritmo de Manejo Agudo (Resucitación)**: Metas, Primera Línea, Dosis.
            3. **Soporte Vital y Procedimientos**
            4. **Semáforo de Evidencia**
            5. **Poblaciones Especiales**
            TONO: Estrictamente técnico.
            `;
            const res = await llamarIA(prompt);
            if(res) document.getElementById('analisis-content').innerHTML = marked.parse(limpiarTexto(res));
        }

        // HILO 2: INFOGRAFÍA VISUAL
        async function procesarInfografiaVisual() {
            // Paso A: Generar HTML del Póster
            const promptPoster = `
            Actúa como Diseñador Gráfico Médico. Genera HTML para un PÓSTER CIENTÍFICO.
            REGLAS: SOLO HTML. No Markdown. Estructura exacta con clases CSS: .poster-header, .poster-body, .traffic-grid, .numbers-grid, .poster-footer.
            Dentro de .poster-body incluye un div vacío: <div id="mermaid-placeholder" class="poster-mermaid"></div>
            `;
            
            const html = await llamarIA(promptPoster);
            if(html) {
                const cleanHtml = limpiarTexto(html);
                document.getElementById('infografia-visual-container').innerHTML = cleanHtml;
                
                // Paso B (Anidado): Una vez tenemos el HTML, generamos el gráfico Mermaid
                // Esto es rápido y corre mientras el usuario lee el texto
                const target = document.getElementById('mermaid-placeholder');
                if(target) {
                    target.innerHTML = "<h4>Algoritmo de Flujo</h4><div>Generando gráfico...</div>";
                    const promptMermaid = `Crea diagrama 'mermaid graph TD' SIMPLE (max 10 nodos). IDs cortos. TEXTOS ENTRE COMILLAS DOBLES. Solo código.`;
                    const mer = await llamarIA(promptMermaid);
                    if(mer) {
                        const cleanM = limpiarMermaid(mer);
                        target.innerHTML = `<div class="mermaid">${cleanM}</div>`;
                        try { mermaid.run(); } catch(e){}
                    }
                }
                
                // Mostrar botón descarga si estamos en la pestaña
                if(document.getElementById('tab-infografia').classList.contains('active')) {
                    document.getElementById('btn-save-img').style.display = 'block';
                }
            }
        }

        // --- UTILIDADES ---
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

        // --- CHAT Y DESCARGA ---
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
