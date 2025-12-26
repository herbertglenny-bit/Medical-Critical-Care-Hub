import streamlit as st
import streamlit.components.v1 as components

# Configuración de página
st.set_page_config(page_title="Estación Médica IA", layout="wide")

# --- SEGURIDAD: LEEMOS LA CLAVE DESDE LOS SECRETOS ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except (FileNotFoundError, KeyError):
    st.error("⚠️ Error Crítico: No se encuentra 'GEMINI_API_KEY' en los Secrets.")
    st.info("Configúrala en: Streamlit Cloud -> Settings -> Secrets")
    st.stop()
# -----------------------------------------------------

html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Estación Médica V23</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    </script>
    
    <style>
        /* ESTILOS GENERALES */
        body { font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background-color: #f0f2f5; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
        
        /* BARRA SUPERIOR */
        #drop-zone { background-color: #e8f0fe; border-bottom: 2px dashed #4285F4; color: #1967d2; padding: 12px; text-align: center; font-weight: bold; cursor: pointer; transition: 0.3s; }
        #drop-zone:hover, #drop-zone.dragover { background-color: #d2e3fc; padding: 20px; }
        
        /* ESTRUCTURA PRINCIPAL */
        .main-container { display: flex; flex: 1; height: calc(100vh - 60px); }
        .pdf-section { width: 50%; border-right: 1px solid #ccc; background: #525659; display: flex; flex-direction: column; overflow: hidden; }
        .pdf-toolbar { background: #333; padding: 8px; display: flex; gap: 10px; justify-content: center; align-items: center; color: white; box-shadow: 0 2px 5px rgba(0,0,0,0.2); z-index: 10; flex-shrink: 0; }
        .pdf-scroll-container { flex: 1; overflow: auto; background-color: #525659; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        .pdf-page-canvas { box-shadow: 0 4px 10px rgba(0,0,0,0.3); background: white; margin-bottom: 15px; flex-shrink: 0; }
        
        .right-panel { width: 50%; display: flex; flex-direction: column; background: white; }
        .tabs-header { display: flex; background: #f1f3f4; border-bottom: 1px solid #ccc; }
        .tab-btn { flex: 1; padding: 15px; border: none; background: transparent; cursor: pointer; font-weight: bold; color: #5f6368; border-bottom: 3px solid transparent; }
        .tab-btn.active { color: #1a73e8; border-bottom: 3px solid #1a73e8; background: white; }
        .tab-content { flex: 1; padding: 25px; overflow-y: auto; display: none; }
        .tab-content.active { display: block; }

        /* MARKDOWN CLÍNICO */
        .markdown-body { line-height: 1.6; color: #333; font-size: 0.95rem; }
        .markdown-body h1, .markdown-body h2 { color: #1a73e8; border-bottom: 2px solid #eee; margin-top: 25px; }
        .markdown-body strong { color: #d93025; font-weight: 700; } 

        /* === DISEÑO DE INFOGRAFÍA VISUAL (Para capturar como imagen) === */
        #infografia-visual-container {
            background: white;
            padding: 40px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            border-radius: 8px;
            max-width: 900px;
            margin: auto;
            border-top: 10px solid #1a73e8; /* Borde estético superior */
        }
        .info-header { text-align: center; margin-bottom: 40px; border-bottom: 2px solid #eee; padding-bottom: 20px; }
        .info-title { font-size: 2.2em; color: #202124; margin: 0; font-weight: 900; text-transform: uppercase; letter-spacing: 1px; }
        .info-subtitle { font-size: 1.2em; color: #1a73e8; font-weight: 500; margin-top: 10px; }
        
        /* Semáforo */
        .info-grid-semaforo { display: flex; gap: 20px; margin-bottom: 40px; }
        .info-box { flex: 1; padding: 20px; border-radius: 8px; color: white; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
        .info-box h3 { margin-top: 0; border-bottom: 1px solid rgba(255,255,255,0.4); padding-bottom: 10px; font-size: 1.1em; }
        .info-box ul { padding-left: 20px; margin-bottom: 0; }
        .info-box li { margin-bottom: 5px; }
        .box-stop { background: #d93025; }
        .box-caution { background: #f9ab00; color: #202124; }
        .box-caution h3 { border-bottom: 1px solid rgba(0,0,0,0.2); }
        .box-go { background: #188038; }

        /* Big Numbers */
        .info-big-numbers-container { display: flex; flex-wrap: wrap; gap: 20px; justify-content: space-around; margin: 40px 0; padding: 25px; background: #f1f3f4; border-radius: 12px; }
        .info-big-number-item { text-align: center; flex: 1 1 180px; }
        .info-number-val { display: block; font-size: 2.5em; font-weight: 900; color: #1a73e8; line-height: 1; }
        .info-number-desc { font-size: 0.95em; color: #555; margin-top: 5px; font-weight: 600; text-transform: uppercase; }

        /* Footer */
        .info-footer { background: #e8f0fe; padding: 25px; border-radius: 8px; margin-top: 40px; border-left: 5px solid #1a73e8; }
        .info-footer h3 { margin-top: 0; color: #1a73e8; }
        
        /* BOTONES */
        button { cursor: pointer; padding: 8px 15px; border-radius: 4px; border: none; background: white; font-weight: bold; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
        button:hover { background: #f1f1f1; }
        .btn-download { background-color: #4CAF50; color: white; text-decoration: none; padding: 8px 15px; border-radius: 4px; font-size: 14px; display: none; }
        .btn-img-dl { background-color: #FF5722; color: white; margin-left: 10px; display: none; transition: 0.3s; }
        .btn-img-dl:hover { background-color: #E64A19; transform: scale(1.05); }

        /* CHAT */
        #chat-container { display: flex; flex-direction: column; height: 100%; }
        #chat-history { flex: 1; overflow-y: auto; margin-bottom: 10px; }
        .msg { margin-bottom: 10px; padding: 12px; border-radius: 12px; max-width: 85%; }
        .msg.user { background: #e8f0fe; align-self: flex-end; color: #1a73e8; }
        .msg.ai { background: #fff; border: 1px solid #ddd; align-self: flex-start; }
        .chat-input-area { display: flex; gap: 10px; padding-top: 10px; border-top: 1px solid #eee; }
        #user-input { flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 20px; outline: none; }
    </style>
</head>
<body>

    <div id="drop-zone">📄 ARRASTRA TU PDF AQUÍ (V23: Suite Completa)</div>

    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button onclick="ajustarZoom(-0.2)">➖ Zoom</button>
                <span id="zoom-level" style="min-width: 50px; text-align: center;">100%</span>
                <button onclick="ajustarZoom(0.2)">➕ Zoom</button>
                <a id="btn-download" class="btn-download" download="documento.pdf">⬇️ PDF</a>
                <button id="btn-img-dl" class="btn-img-dl" onclick="descargarInfografia()">📸 Guardar Infografía</button>
            </div>
            <div id="pdf-container" class="pdf-scroll-container"></div>
        </div>

        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="abrirPestana('tab-analisis')">📝 Análisis Técnico</button>
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">🎨 Infografía Visual</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">💬 Discusión</button>
            </div>
            
            <div id="tab-analisis" class="tab-content active">
                <div id="analisis-content" class="markdown-body">
                    <p style="color:#666; text-align:center; margin-top:50px;">
                        Esperando documento...
                    </p>
                </div>
            </div>

            <div id="tab-infografia" class="tab-content">
                <div id="infografia-visual-container">
                    <p style="color:#666; text-align:center; margin-top:50px;">
                        Aquí aparecerá tu resumen visual descargable.
                    </p>
                </div>
                <div id="mermaid-section-container" style="margin-top: 30px;"></div>
            </div>

            <div id="tab-chat" class="tab-content">
                <div id="chat-container">
                    <div id="chat-history"></div>
                    <div class="chat-input-area">
                        <input type="text" id="user-input" placeholder="Pregunta al experto..." onkeypress="if(event.key==='Enter') enviarMensaje()">
                        <button onclick="enviarMensaje()">Enviar</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // --- INYECCIÓN DE CLAVE ---
        const API_KEY = "__API_KEY_PLACEHOLDER__"; 

        // --- MODELOS (Priorizando NanoBanana/Gemini 2.x) ---
        const MODEL_CANDIDATES = [
            "gemini-2.0-flash", 
            "gemini-2.5-flash",
            "gemini-1.5-pro",
            "gemini-pro"
        ];
        let WORKING_MODEL = null;

        let pdfDoc = null, scale = 1.0, rotation = 0, globalPdfBase64 = null;
        mermaid.initialize({ startOnLoad: false, theme: 'neutral' });

        // --- GESTIÓN DE PESTAÑAS ---
        function abrirPestana(id) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            
            // Gestión botones superiores
            const btnImg = document.getElementById('btn-img-dl');
            if(id === 'tab-infografia' && document.querySelector('.info-title')) {
                btnImg.style.display = 'inline-block';
            } else {
                btnImg.style.display = 'none';
            }

            // Highlight tabs visual
            if(id.includes('analisis')) document.querySelectorAll('.tab-btn')[0].classList.add('active');
            if(id.includes('infografia')) document.querySelectorAll('.tab-btn')[1].classList.add('active');
            if(id.includes('chat')) document.querySelectorAll('.tab-btn')[2].classList.add('active');
        }

        // --- FUNCIÓN DE DESCARGA DE IMAGEN ---
        function descargarInfografia() {
            const domNode = document.getElementById('infografia-visual-container');
            // Usamos html2canvas con escala x2 para alta resolución
            html2canvas(domNode, { scale: 2, useCORS: true }).then(canvas => {
                const a = document.createElement('a');
                a.href = canvas.toDataURL('image/png');
                a.download = 'Infografia_Medica_IA.png';
                a.click();
            });
        }

        // --- CARGA DE PDF ---
        const dropZone = document.getElementById('drop-zone');
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
        dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('dragover'); });
        
        dropZone.addEventListener('drop', async (e) => {
            e.preventDefault(); dropZone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if(file && file.type === "application/pdf") {
                dropZone.innerText = "⏳ Procesando...";
                const fileURL = URL.createObjectURL(file);
                document.getElementById('btn-download').href = fileURL;
                document.getElementById('btn-download').style.display = 'inline-block';
                cargarPDF(fileURL);
                const reader = new FileReader();
                reader.onload = async () => {
                    globalPdfBase64 = reader.result.split(',')[1];
                    procesarIA();
                };
                reader.readAsDataURL(file);
            }
        });

        async function cargarPDF(url) { pdfDoc = await pdfjsLib.getDocument(url).promise; renderizarTodo(); }
        async function renderizarTodo() {
            const container = document.getElementById('pdf-container'); container.innerHTML = "";
            document.getElementById('zoom-level').innerText = Math.round(scale * 100) + "%";
            container.style.alignItems = scale > 1.0 ? "flex-start" : "center";
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

        function limpiarMarkdown(t) { return t.replace(/```html|```|<!DOCTYPE html>|<html>|<\/html>|<head>[\s\S]*?<\/head>|<body>|<\/body>/gi, "").trim(); }
        function limpiarMermaid(t) { let l = t.replace(/```mermaid|```/gi, ""); const i = l.indexOf("graph TD"); if(i !== -1) l = l.substring(i); return l.trim(); }

        // --- CEREBRO IA ---
        async function procesarIA() {
            // FASE 1: ANÁLISIS TÉCNICO (Markdown)
            dropZone.innerText = "🤖 Fase 1: Análisis...";
            document.getElementById('analisis-content').innerHTML = "<div class='msg ai'>🧠 Diseccionando guía clínica (Modo Experto)...</div>";
            
            const promptAnalisis = `
            # OBJETIVO
            Destacando aspectos de Medicina Intensiva y Medicina Basada en la Evidencia. Realiza una disección técnica exhaustiva de la GPC.
            # ESTRUCTURA (MARKDOWN)
            1. Definiciones/Criterios
            2. Algoritmo Agudo (Metas, Dosis)
            3. Soporte Vital
            4. Semáforo Evidencia
            5. Poblaciones
            6. Ingreso/Alta
            * Tono profesional neutro.
            `;
            let resAnalisis = await intentarLlamadaRobusta(promptAnalisis);
            if(resAnalisis) document.getElementById('analisis-content').innerHTML = marked.parse(limpiarMarkdown(resAnalisis));

            // FASE 2: INFOGRAFÍA VISUAL (HTML Estructurado)
            dropZone.innerText = "🎨 Fase 2: Diseñando...";
            const containerVisual = document.getElementById('infografia-visual-container');
            containerVisual.innerHTML = "<div class='msg ai'>🎨 Maquetando infografía de alto impacto...</div>";

            const promptInfografiaHTML = `
            Actúa como Diseñador Médico. Crea el contenido para una Infografía Visual de la guía.
            Devuelve SOLO CÓDIGO HTML que siga ESTA ESTRUCTURA EXACTA (sin markdown):
            
            <div class="info-header">
                <h1 class="info-title">TITULO CORTO E IMPACTANTE</h1>
                <p class="info-subtitle">Subtítulo / Población / Año</p>
            </div>

            <div class="info-grid-semaforo">
                <div class="info-box box-stop">
                    <h3>🔴 STOP (No hacer)</h3>
                    <ul><li>Práctica 1</li><li>Práctica 2</li></ul>
                </div>
                <div class="info-box box-caution">
                    <h3>🟡 PRECAUCIÓN</h3>
                    <ul><li>Área gris 1</li><li>Área gris 2</li></ul>
                </div>
                <div class="info-box box-go">
                    <h3>🟢 GO (Hacer)</h3>
                    <ul><li>Recomendación fuerte 1</li><li>Recomendación fuerte 2</li></ul>
                </div>
            </div>

            <div class="info-big-numbers-container">
                <div class="info-big-number-item">
                    <span class="info-number-val">DATOS</span>
                    <span class="info-number-desc">Contexto</span>
                </div>
            </div>

            <div class="info-footer">
                <h3>🚀 TAKE HOME MESSAGES</h3>
                <ul>
                    <li>Mensaje 1.</li>
                    <li>Mensaje 2.</li>
                    <li>Mensaje 3.</li>
                </ul>
            </div>
            `;

            let resInfoHTML = await intentarLlamadaRobusta(promptInfografiaHTML);
            if(resInfoHTML) {
                containerVisual.innerHTML = limpiarMarkdown(resInfoHTML);
                
                // Diagrama Mermaid debajo
                document.getElementById('mermaid-section-container').innerHTML = "<hr><h3>🔄 Algoritmo de Flujo</h3><div id='mermaid-in'>Generando...</div>";
                let resMermaid = await llamarGemini(`Crea diagrama 'mermaid graph TD' del Algoritmo de Manejo. SOLO CÓDIGO.`, WORKING_MODEL);
                if(resMermaid && !resMermaid.startsWith("Error")) {
                    document.getElementById('mermaid-in').innerHTML = `<div class="mermaid">${limpiarMermaid(resMermaid)}</div>`;
                    try { mermaid.run(); } catch(e) { }
                }
                dropZone.innerText = "✅ Listo";
                
                // Si estamos en la pestaña infografía, mostramos botón
                if(document.getElementById('tab-infografia').classList.contains('active')) {
                    document.getElementById('btn-img-dl').style.display = 'inline-block';
                }
            }
        }

        async function intentarLlamadaRobusta(prompt) {
            if (WORKING_MODEL) return await llamarGemini(prompt, WORKING_MODEL);
            for (let modelo of MODEL_CANDIDATES) {
                const res = await llamarGemini(prompt, modelo);
                if (res && !res.startsWith("Error")) { WORKING_MODEL = modelo; return res; }
            }
            return null;
        }

        async function enviarMensaje() {
            const i = document.getElementById('user-input'), h = document.getElementById('chat-history');
            const t = i.value; if(!t) return;
            h.innerHTML += `<div class="msg user">${t}</div>`; i.value = ""; h.scrollTop = h.scrollHeight;
            const resRaw = await intentarLlamadaRobusta(`Respuesta técnica breve: ${t}`);
            h.innerHTML += resRaw ? `<div class="msg ai">${marked.parse(limpiarMarkdown(resRaw))}</div>` : `<div class="msg ai" style="color:red">Error.</div>`;
            h.scrollTop = h.scrollHeight;
        }

        async function llamarGemini(prompt, modelo) {
            if(!globalPdfBase64) return "Error: Sin PDF";
            try {
                const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${modelo}:generateContent?key=${API_KEY}`, {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ contents: [{ parts: [{ text: prompt }, { inline_data: { mime_type: "application/pdf", data: globalPdfBase64 } }] }] })
                });
                const d = await r.json();
                if(d.error) return "Error: " + d.error.message;
                return d.candidates[0].content.parts[0].text;
            } catch(e) { return "Error Red"; }
        }
    </script>
</body>
</html>
"""

final_html = html_template.replace("__API_KEY_PLACEHOLDER__", API_KEY)
components.html(final_html, height=1000, scrolling=True)
