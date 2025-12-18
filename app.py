import streamlit as st
import streamlit.components.v1 as components

# Configuración de página
st.set_page_config(page_title="Estación Médica IA", layout="wide")

# --- AQUÍ DEFINIMOS TU API KEY (Pégala abajo entre las comillas) ---
API_KEY = "AIzaSyCG20t5xU50wAY-yv1oNcen5738ZqPFSag" 
# ------------------------------------------------------------------

# El código HTML/JS completo incrustado directamente en Python
# Así nos aseguramos de que SIEMPRE se cargue la versión correcta.
html_code = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Estación Médica</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    </script>
    <style>
        body {{ font-family: sans-serif; margin: 0; padding: 0; background-color: #f0f2f5; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }}
        #drop-zone {{ background-color: #e8f0fe; border-bottom: 2px dashed #4285F4; color: #1967d2; padding: 15px; text-align: center; font-weight: bold; cursor: pointer; }}
        #drop-zone.dragover {{ background-color: #d2e3fc; }}
        .main-container {{ display: flex; flex: 1; height: calc(100vh - 60px); }}
        
        /* IZQUIERDA */
        .pdf-section {{ width: 50%; border-right: 1px solid #ccc; background: #525659; display: flex; flex-direction: column; }}
        .pdf-toolbar {{ background: #333; padding: 8px; display: flex; gap: 10px; justify-content: center; color: white; }}
        .pdf-scroll-container {{ flex: 1; overflow: auto; display: flex; justify-content: center; padding: 20px; }}
        #pdf-render {{ box-shadow: 0 0 10px rgba(0,0,0,0.5); background: white; max-width: 95%; }}
        
        /* DERECHA */
        .right-panel {{ width: 50%; display: flex; flex-direction: column; background: white; }}
        .tabs-header {{ display: flex; background: #f1f3f4; border-bottom: 1px solid #ccc; }}
        .tab-btn {{ flex: 1; padding: 15px; border: none; background: transparent; cursor: pointer; font-weight: bold; color: #5f6368; border-bottom: 3px solid transparent; }}
        .tab-btn.active {{ color: #1a73e8; border-bottom: 3px solid #1a73e8; background: white; }}
        .tab-content {{ flex: 1; padding: 20px; overflow-y: auto; display: none; }}
        .tab-content.active {{ display: block; }}
        
        /* Chat y Markdown */
        .markdown-body {{ line-height: 1.6; color: #333; }}
        .markdown-body h3 {{ color: #1a73e8; border-bottom: 1px solid #eee; }}
        #chat-container {{ display: flex; flex-direction: column; height: 100%; }}
        #chat-history {{ flex: 1; overflow-y: auto; margin-bottom: 10px; }}
        .chat-input-area {{ display: flex; gap: 10px; padding-top: 10px; border-top: 1px solid #eee; }}
        #user-input {{ flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 20px; }}
        .msg {{ margin-bottom: 10px; padding: 10px 15px; border-radius: 15px; max-width: 85%; }}
        .msg.user {{ background: #e8f0fe; align-self: flex-end; margin-left: auto; }}
        .msg.ai {{ background: #f1f3f4; align-self: flex-start; }}
        button {{ cursor: pointer; }}
    </style>
</head>
<body>
    <div id="drop-zone">📄 ARRASTRA TU PDF MÉDICO AQUÍ (Nueva Versión)</div>
    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button onclick="cambiarPagina(-1)">⬅️</button>
                <span id="page-num">Pág 0</span>
                <button onclick="cambiarPagina(1)">➡️</button>
                <button onclick="rotarPDF()">🔄 Rotar</button>
            </div>
            <div class="pdf-scroll-container">
                <canvas id="pdf-render"></canvas>
            </div>
        </div>
        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="abrirPestana('tab-analisis')">📝 Análisis</button>
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">📊 Infografía</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">💬 Chat</button>
            </div>
            <div id="tab-analisis" class="tab-content active"><div id="analisis-content" class="markdown-body">Arrastra un PDF...</div></div>
            <div id="tab-infografia" class="tab-content"><div id="infografia-content">Gráfico pendiente...</div></div>
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
        const API_KEY = "{API_KEY}"; // Aquí Python inyecta tu clave automáticamente
        
        let pdfDoc = null, pageNum = 1, scale = 1.2, rotation = 0, globalPdfBase64 = null;
        const canvas = document.getElementById('pdf-render');
        const ctx = canvas.getContext('2d');
        const dropZone = document.getElementById('drop-zone');

        mermaid.initialize({{ startOnLoad: false, theme: 'default' }});

        function abrirPestana(id) {{
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            // Activar botón visualmente (simplificado)
            if(id.includes('analisis')) document.querySelectorAll('.tab-btn')[0].classList.add('active');
            if(id.includes('infografia')) document.querySelectorAll('.tab-btn')[1].classList.add('active');
            if(id.includes('chat')) document.querySelectorAll('.tab-btn')[2].classList.add('active');
        }}

        dropZone.addEventListener('dragover', (e) => {{ e.preventDefault(); dropZone.classList.add('dragover'); }});
        dropZone.addEventListener('dragleave', () => {{ dropZone.classList.remove('dragover'); }});
        dropZone.addEventListener('drop', async (e) => {{
            e.preventDefault(); dropZone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if(file && file.type === "application/pdf") {{
                dropZone.innerText = "⏳ Procesando...";
                const fileURL = URL.createObjectURL(file);
                // Cargar PDF visual
                pdfjsLib.getDocument(fileURL).promise.then(doc => {{
                    pdfDoc = doc; pageNum = 1; renderPage(1);
                    document.getElementById('page-num').innerText = "Pág 1/" + pdfDoc.numPages;
                }});
                // Leer base64 para IA
                const reader = new FileReader();
                reader.onload = async () => {{
                    globalPdfBase64 = reader.result.split(',')[1];
                    // Lanzar tareas IA
                    document.getElementById('analisis-content').innerHTML = "🧠 Analizando...";
                    document.getElementById('infografia-content').innerHTML = "🎨 Diseñando...";
                    
                    const pAnalisis = `Analiza este estudio médico. HTML limpio con: Título, Metodología, Resultados (datos en negrita) y Conclusión.`;
                    const resAnalisis = await llamarGemini(pAnalisis, globalPdfBase64);
                    document.getElementById('analisis-content').innerHTML = marked.parse(resAnalisis);

                    const pInfo = `Crea un diagrama de flujo simple Mermaid graph TD del estudio. SOLO CÓDIGO.`;
                    let resInfo = await llamarGemini(pInfo, globalPdfBase64);
                    resInfo = resInfo.replace(/```mermaid/g, '').replace(/```/g, '').trim();
                    document.getElementById('infografia-content').innerHTML = `<div class="mermaid">${{resInfo}}</div>`;
                    mermaid.run();
                    
                    dropZone.innerText = "✅ Listo";
                }};
                reader.readAsDataURL(file);
            }}
        }});

        function renderPage(num) {{
            if(!pdfDoc) return;
            pdfDoc.getPage(num).then(page => {{
                const viewport = page.getViewport({{scale: scale, rotation: rotation}});
                canvas.height = viewport.height; canvas.width = viewport.width;
                page.render({{canvasContext: ctx, viewport: viewport}});
            }});
        }}
        function cambiarPagina(d) {{ if(pdfDoc && pageNum+d > 0 && pageNum+d <= pdfDoc.numPages) {{ pageNum+=d; renderPage(pageNum); document.getElementById('page-num').innerText = "Pág "+pageNum+"/"+pdfDoc.numPages; }} }}
        function rotarPDF() {{ rotation = (rotation+90)%360; renderPage(pageNum); }}

        async function enviarMensaje() {{
            const input = document.getElementById('user-input');
            const txt = input.value;
            if(!txt) return;
            document.getElementById('chat-history').innerHTML += `<div class="msg user">${{txt}}</div>`;
            input.value = "";
            const res = await llamarGemini(`Responde brevemente según el PDF: ${{txt}}`, globalPdfBase64);
            document.getElementById('chat-history').innerHTML += `<div class="msg ai">${{marked.parse(res)}}</div>`;
        }}

        async function llamarGemini(txt, b64) {{
            if(!b64) return "Error: No hay PDF cargado.";
            try {{
                const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${{API_KEY}}`, {{
                    method: 'POST', headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ contents: [{{ parts: [{{ text: txt }}, {{ inline_data: {{ mime_type: "application/pdf", data: b64 }} }}] }}] }})
                }});
                const d = await r.json();
                if(d.error) return "Error API: " + d.error.message;
                return d.candidates[0].content.parts[0].text;
            }} catch(e) {{ return "Error de red."; }}
        }}
    </script>
</body>
</html>
"""

components.html(html_code, height=1000, scrolling=True)
