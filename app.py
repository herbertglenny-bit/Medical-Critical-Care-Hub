import streamlit as st
import streamlit.components.v1 as components

# Configuración de página
st.set_page_config(page_title="Estación Médica IA", layout="wide")

# --- ¡PEGA TU API KEY AQUÍ! ---
API_KEY = "AIzaSyCG20t5xU50wAY-yv1oNcen5738ZqPFSag"
# ------------------------------

# NOTA: He quitado la 'f' del principio para evitar conflictos con JavaScript
html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Estación Médica V11</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    </script>
    
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background-color: #f0f2f5; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
        
        /* ZONA DE ARRASTRE */
        #drop-zone { background-color: #e8f0fe; border-bottom: 2px dashed #4285F4; color: #1967d2; padding: 12px; text-align: center; font-weight: bold; cursor: pointer; transition: 0.3s; }
        #drop-zone:hover, #drop-zone.dragover { background-color: #d2e3fc; padding: 20px; }
        
        /* CONTENEDOR PRINCIPAL */
        .main-container { display: flex; flex: 1; height: calc(100vh - 60px); }
        
        /* IZQUIERDA */
        .pdf-section { width: 50%; border-right: 1px solid #ccc; background: #525659; display: flex; flex-direction: column; overflow: hidden; }
        .pdf-toolbar { background: #333; padding: 8px; display: flex; gap: 10px; justify-content: center; align-items: center; color: white; box-shadow: 0 2px 5px rgba(0,0,0,0.2); z-index: 10; flex-shrink: 0; }
        
        /* SCROLL */
        .pdf-scroll-container { flex: 1; overflow: auto; background-color: #525659; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        .pdf-page-canvas { box-shadow: 0 4px 10px rgba(0,0,0,0.3); background: white; margin-bottom: 15px; flex-shrink: 0; }

        /* Botones */
        button { cursor: pointer; padding: 6px 12px; border-radius: 4px; border: none; background: white; font-weight: bold; font-size: 14px; }
        button:hover { background: #ddd; }
        .btn-download { background-color: #4CAF50; color: white; text-decoration: none; padding: 6px 12px; border-radius: 4px; font-size: 14px; display: none; }
        
        /* DERECHA */
        .right-panel { width: 50%; display: flex; flex-direction: column; background: white; }
        .tabs-header { display: flex; background: #f1f3f4; border-bottom: 1px solid #ccc; }
        .tab-btn { flex: 1; padding: 15px; border: none; background: transparent; cursor: pointer; font-weight: bold; color: #5f6368; border-bottom: 3px solid transparent; }
        .tab-btn.active { color: #1a73e8; border-bottom: 3px solid #1a73e8; background: white; }
        .tab-content { flex: 1; padding: 25px; overflow-y: auto; display: none; }
        .tab-content.active { display: block; }
        
        /* Estilos Texto */
        .markdown-body { line-height: 1.6; color: #333; }
        .markdown-body h1, .markdown-body h2, .markdown-body h3 { color: #1a73e8; border-bottom: 1px solid #eee; margin-top: 20px; }
        .error-box { background: #fce8e6; color: #c5221f; padding: 10px; border: 1px solid #f2b2ae; font-family: monospace; }
        
        /* Chat */
        #chat-container { display: flex; flex-direction: column; height: 100%; }
        #chat-history { flex: 1; overflow-y: auto; margin-bottom: 10px; }
        .msg { margin-bottom: 10px; padding: 10px; border-radius: 10px; max-width: 85%; }
        .msg.user { background: #e8f0fe; align-self: flex-end; }
        .msg.ai { background: #f1f3f4; align-self: flex-start; }
        .chat-input-area { display: flex; gap: 10px; padding-top: 10px; border-top: 1px solid #eee; }
        #user-input { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 20px; }
    </style>
</head>
<body>

    <div id="drop-zone">📄 ARRASTRA TU PDF AQUÍ (V11 Final)</div>

    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button onclick="ajustarZoom(-0.2)">➖ Zoom</button>
                <span id="zoom-level" style="min-width: 50px; text-align: center;">100%</span>
                <button onclick="ajustarZoom(0.2)">➕ Zoom</button>
                <button onclick="rotarPDF()">🔄 Rotar</button>
                <a id="btn-download" class="btn-download" download="documento.pdf">⬇️ Descargar</a>
            </div>
            <div id="pdf-container" class="pdf-scroll-container"></div>
        </div>

        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="abrirPestana('tab-analisis')">📝 Análisis</button>
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">📊 Infografía</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">💬 Chat</button>
            </div>
            
            <div id="tab-analisis" class="tab-content active">
                <div id="analisis-content" class="markdown-body">
                    <p style="color:#666; text-align:center; margin-top:50px;">Esperando archivo...</p>
                </div>
            </div>
            <div id="tab-infografia" class="tab-content">
                <div id="infografia-content" class="markdown-body"></div>
            </div>
            <div id="tab-chat" class="tab-content">
                <div id="chat-container">
                    <div id="chat-history"></div>
                    <div class="chat-input-area">
                        <input type="text" id="user-input" placeholder="Pregunta algo..." onkeypress="if(event.key==='Enter') enviarMensaje()">
                        <button onclick="enviarMensaje()">Enviar</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // INYECCIÓN DE CLAVE SEGURA
        const API_KEY = "__API_KEY_PLACEHOLDER__"; 

        // Lista de modelos a probar (Auto-Detect)
        const MODEL_CANDIDATES = [
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash-001",
            "gemini-1.5-pro",
            "gemini-1.5-pro-latest"
        ];
        let WORKING_MODEL = null;

        let pdfDoc = null, scale = 1.0, rotation = 0, globalPdfBase64 = null;
        mermaid.initialize({ startOnLoad: false, theme: 'neutral' });

        function abrirPestana(id) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            // Activar botón visualmente
            if(id.includes('analisis')) document.querySelectorAll('.tab-btn')[0].classList.add('active');
            if(id.includes('infografia')) document.querySelectorAll('.tab-btn')[1].classList.add('active');
            if(id.includes('chat')) document.querySelectorAll('.tab-btn')[2].classList.add('active');
        }

        const dropZone = document.getElementById('drop-zone');
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
        dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('dragover'); });
        
        dropZone.addEventListener('drop', async (e) => {
            e.preventDefault(); dropZone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if(file && file.type === "application/pdf") {
                dropZone.innerText = "⏳ Procesando...";
                const fileURL = URL.createObjectURL(file);
                const db = document.getElementById('btn-download');
                db.href = fileURL; db.download = file.name; db.style.display = "inline-block";
                cargarPDF(fileURL);
                const reader = new FileReader();
                reader.onload = async () => {
                    globalPdfBase64 = reader.result.split(',')[1];
                    procesarIA();
                };
                reader.readAsDataURL(file);
            }
        });

        async function cargarPDF(url) {
            pdfDoc = await pdfjsLib.getDocument(url).promise;
            renderizarTodo();
        }

        async function renderizarTodo() {
            const container = document.getElementById('pdf-container');
            container.innerHTML = "";
            document.getElementById('zoom-level').innerText = Math.round(scale * 100) + "%";
            
            // Fix alineación scroll
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
        function rotarPDF() { if(pdfDoc) { rotation = (rotation + 90) % 360; renderizarTodo(); } }

        // --- IA CON AUTO-DETECT ---
        async function procesarIA() {
            dropZone.innerText = "🤖 Buscando modelo IA...";
            document.getElementById('analisis-content').innerHTML = "<div class='msg ai'>🧠 Probando conexión con Google Gemini...</div>";

            const prompt = `Analiza este PDF médico. HTML limpio con: <h3>🏥 Título</h3> <h3>🎯 Objetivo</h3> <h3>📊 Metodología</h3> <h3>💊 Resultados Clave (Negrita)</h3> <h3>⚠️ Conclusiones</h3>`;
            
            const html = await intentarLlamadaRobusta(prompt);
            
            if(html) {
                document.getElementById('analisis-content').innerHTML = marked.parse(html);
                
                // Infografía
                document.getElementById('infografia-content').innerHTML = "<div class='msg ai'>Generando gráfico...</div>";
                let mermaidCode = await llamarGemini(`Crea un diagrama mermaid graph TD del estudio. SOLO CÓDIGO.`, WORKING_MODEL);
                if(mermaidCode && !mermaidCode.startsWith("Error")) {
                    mermaidCode = mermaidCode.replace(/```mermaid/g, '').replace(/```/g, '').trim();
                    document.getElementById('infografia-content').innerHTML = `<div class="mermaid">${mermaidCode}</div>`;
                    try { mermaid.run(); } catch(e){}
                }
                dropZone.innerText = "✅ Listo (" + WORKING_MODEL + ")";
            }
        }

        async function intentarLlamadaRobusta(prompt) {
            if (WORKING_MODEL) return await llamarGemini(prompt, WORKING_MODEL);
            
            let errores = [];
            for (let modelo of MODEL_CANDIDATES) {
                // Ahora esto es JavaScript puro, no Python, así que no falla
                console.log(`Probando ${modelo}...`);
                
                const res = await llamarGemini(prompt, modelo);
                if (res && !res.startsWith("Error")) {
                    WORKING_MODEL = modelo;
                    return res;
                } else {
                    errores.push(`${modelo}: ${res}`);
                }
            }
            document.getElementById('analisis-content').innerHTML = `<div class="error-box"><b>Fallo Total:</b><br>${errores.join('<br>')}</div>`;
            return null;
        }

        async function enviarMensaje() {
            const i = document.getElementById('user-input');
            const t = i.value; if(!t) return;
            const h = document.getElementById('chat-history');
            h.innerHTML += `<div class="msg user">${t}</div>`; i.value = "";
            const r = await intentarLlamadaRobusta(`Responde brevemente según el PDF: ${t}`);
            if(r) h.innerHTML += `<div class="msg ai">${marked.parse(r)}</div>`;
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

# AQUÍ HACEMOS LA SUSTITUCIÓN SEGURA DE LA CLAVE
# Esto evita que Python intente leer el código JavaScript
final_html = html_template.replace("__API_KEY_PLACEHOLDER__", API_KEY)

components.html(final_html, height=1000, scrolling=True)
