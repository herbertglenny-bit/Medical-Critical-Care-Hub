import streamlit as st
import streamlit.components.v1 as components

# Configuración de página
st.set_page_config(page_title="Estación Médica IA", layout="wide")

# --- ¡PEGA TU API KEY AQUÍ! ---
API_KEY = "AIzaSyCG20t5xU50wAY-yv1oNcen5738ZqPFSag"
# ------------------------------

html_code = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Estación Médica V10 (Auto-Fix)</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    </script>
    
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; background-color: #f0f2f5; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }}
        
        /* ZONA DE ARRASTRE */
        #drop-zone {{ background-color: #e8f0fe; border-bottom: 2px dashed #4285F4; color: #1967d2; padding: 12px; text-align: center; font-weight: bold; cursor: pointer; transition: 0.3s; }}
        #drop-zone:hover, #drop-zone.dragover {{ background-color: #d2e3fc; padding: 20px; }}
        
        /* CONTENEDOR PRINCIPAL */
        .main-container {{ display: flex; flex: 1; height: calc(100vh - 60px); }}
        
        /* --- IZQUIERDA: PDF --- */
        .pdf-section {{ 
            width: 50%; 
            border-right: 1px solid #ccc; 
            background: #525659; 
            display: flex; 
            flex-direction: column; 
            overflow: hidden; /* El scroll lo maneja el hijo */
        }}
        
        .pdf-toolbar {{ 
            background: #333; padding: 8px; display: flex; gap: 10px; justify-content: center; align-items: center; color: white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2); z-index: 10; flex-shrink: 0;
        }}
        
        /* CORRECCIÓN FINAL DE SCROLL HORIZONTAL Y VERTICAL */
        .pdf-scroll-container {{ 
            flex: 1; 
            overflow: auto; /* Barras de scroll automáticas */
            background-color: #525659;
            padding: 20px;
            display: flex; /* Flex permite centrar pero expandir */
            flex-direction: column;
            align-items: center; /* Centrado inicial */
        }}
        
        /* EL LIENZO DEL PDF */
        .pdf-page-canvas {{ 
            box-shadow: 0 4px 10px rgba(0,0,0,0.3); 
            background: white; 
            margin-bottom: 15px; 
            flex-shrink: 0; /* No permitir que se encoja */
        }}

        /* Botones */
        button {{ cursor: pointer; padding: 6px 12px; border-radius: 4px; border: none; background: white; font-weight: bold; font-size: 14px; }}
        button:hover {{ background: #ddd; }}
        
        .btn-download {{ background-color: #4CAF50; color: white; text-decoration: none; padding: 6px 12px; border-radius: 4px; font-size: 14px; display: none; }}
        
        /* --- DERECHA: PESTAÑAS --- */
        .right-panel {{ width: 50%; display: flex; flex-direction: column; background: white; }}
        .tabs-header {{ display: flex; background: #f1f3f4; border-bottom: 1px solid #ccc; }}
        .tab-btn {{ flex: 1; padding: 15px; border: none; background: transparent; cursor: pointer; font-weight: bold; color: #5f6368; border-bottom: 3px solid transparent; }}
        .tab-btn.active {{ color: #1a73e8; border-bottom: 3px solid #1a73e8; background: white; }}
        
        .tab-content {{ flex: 1; padding: 25px; overflow-y: auto; display: none; }}
        .tab-content.active {{ display: block; }}
        
        /* Markdown y Chat */
        .markdown-body {{ line-height: 1.6; color: #333; }}
        .markdown-body h1, .markdown-body h2, .markdown-body h3 {{ color: #1a73e8; border-bottom: 1px solid #eee; margin-top: 20px; }}
        
        #chat-container {{ display: flex; flex-direction: column; height: 100%; }}
        #chat-history {{ flex: 1; overflow-y: auto; margin-bottom: 10px; padding-right: 5px; }}
        .chat-input-area {{ display: flex; gap: 10px; padding-top: 10px; border-top: 1px solid #eee; }}
        #user-input {{ flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 20px; outline: none; }}
        
        .msg {{ margin-bottom: 12px; padding: 10px 15px; border-radius: 15px; max-width: 85%; line-height: 1.5; }}
        .msg.user {{ background: #e8f0fe; color: #185abc; align-self: flex-end; margin-left: auto; }}
        .msg.ai {{ background: #f1f3f4; align-self: flex-start; }}
        
        .error-box {{ background: #fce8e6; color: #c5221f; padding: 15px; border-radius: 8px; border: 1px solid #f2b2ae; font-family: monospace; font-size: 0.9em; }}
    </style>
</head>
<body>

    <div id="drop-zone">📄 ARRASTRA TU PDF AQUÍ (V10 Auto-Detect)</div>

    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button onclick="ajustarZoom(-0.2)">➖ Zoom</button>
                <span id="zoom-level" style="min-width: 50px; text-align: center;">100%</span>
                <button onclick="ajustarZoom(0.2)">➕ Zoom</button>
                <button onclick="rotarPDF()">🔄 Rotar</button>
                <a id="btn-download" class="btn-download" download="documento.pdf">⬇️ Descargar</a>
            </div>
            <div id="pdf-container" class="pdf-scroll-container">
                </div>
        </div>

        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="abrirPestana('tab-analisis')">📝 Análisis</button>
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">📊 Infografía</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">💬 Chat</button>
            </div>
            
            <div id="tab-analisis" class="tab-content active">
                <div id="analisis-content" class="markdown-body">
                    <p style="color: #666; text-align: center; margin-top: 50px;">
                        Esperando archivo...
                    </p>
                </div>
            </div>
            
            <div id="tab-infografia" class="tab-content">
                <div id="infografia-content" class="markdown-body"></div>
            </div>
            
            <div id="tab-chat" class="tab-content">
                <div id="chat-container">
                    <div id="chat-history"></div>
                    <div class="chat-input-area">
                        <input type="text" id="user-input" placeholder="Pregunta sobre el estudio..." onkeypress="if(event.key==='Enter') enviarMensaje()">
                        <button onclick="enviarMensaje()">Enviar</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_KEY = "{API_KEY}"; 
        
        // LISTA DE MODELOS A PROBAR (En orden de preferencia)
        const MODEL_CANDIDATES = [
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash-001",
            "gemini-1.5-flash-002",
            "gemini-1.5-pro",
            "gemini-1.5-pro-latest"
        ];
        
        let WORKING_MODEL = null; // Aquí guardaremos el que funcione

        let pdfDoc = null;
        let scale = 1.0;
        let rotation = 0;
        let globalPdfBase64 = null;

        mermaid.initialize({{ startOnLoad: false, theme: 'neutral' }});

        function abrirPestana(id) {{
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            
            if(id.includes('analisis')) document.querySelectorAll('.tab-btn')[0].classList.add('active');
            if(id.includes('infografia')) document.querySelectorAll('.tab-btn')[1].classList.add('active');
            if(id.includes('chat')) document.querySelectorAll('.tab-btn')[2].classList.add('active');
        }}

        const dropZone = document.getElementById('drop-zone');
        dropZone.addEventListener('dragover', (e) => {{ e.preventDefault(); dropZone.classList.add('dragover'); }});
        dropZone.addEventListener('dragleave', () => {{ dropZone.classList.remove('dragover'); }});
        
        dropZone.addEventListener('drop', async (e) => {{
            e.preventDefault(); dropZone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];

            if(file && file.type === "application/pdf") {{
                dropZone.innerText = "⏳ Procesando...";
                
                const fileURL = URL.createObjectURL(file);
                const downloadBtn = document.getElementById('btn-download');
                downloadBtn.href = fileURL;
                downloadBtn.download = file.name;
                downloadBtn.style.display = "inline-block";

                cargarPDF(fileURL);

                const reader = new FileReader();
                reader.onload = async () => {{
                    globalPdfBase64 = reader.result.split(',')[1];
                    procesarIA();
                }};
                reader.readAsDataURL(file);
            }}
        }});

        async function cargarPDF(url) {{
            pdfDoc = await pdfjsLib.getDocument(url).promise;
            renderizarTodo();
        }}

        async function renderizarTodo() {{
            const container = document.getElementById('pdf-container');
            container.innerHTML = ""; 
            document.getElementById('zoom-level').innerText = Math.round(scale * 100) + "%";

            // Si el scale es muy grande, align-items: center del contenedor puede impedir scroll
            // Así que si scale > 1, cambiamos alineación
            if(scale > 1.0) {{
                container.style.alignItems = "flex-start";
            }} else {{
                container.style.alignItems = "center";
            }}

            for (let num = 1; num <= pdfDoc.numPages; num++) {{
                const page = await pdfDoc.getPage(num);
                const viewport = page.getViewport({{ scale: scale, rotation: rotation }});
                
                const canvas = document.createElement('canvas');
                canvas.className = 'pdf-page-canvas';
                canvas.height = viewport.height;
                canvas.width = viewport.width;
                container.appendChild(canvas);

                const ctx = canvas.getContext('2d');
                page.render({{ canvasContext: ctx, viewport: viewport }});
            }}
        }}

        function ajustarZoom(delta) {{
            if(!pdfDoc) return;
            scale = Math.max(0.2, scale + delta);
            renderizarTodo();
        }}

        function rotarPDF() {{
            if(!pdfDoc) return;
            rotation = (rotation + 90) % 360;
            renderizarTodo();
        }}

        // --- LÓGICA IA CON AUTO-DESCUBRIMIENTO DE MODELO ---
        async function procesarIA() {{
            dropZone.innerText = "🤖 Buscando modelo compatible...";
            document.getElementById('analisis-content').innerHTML = "<div class='msg ai'>🧠 Detectando modelo de IA disponible...</div>";
            document.getElementById('infografia-content').innerHTML = "<div class='msg ai'>⏳ Esperando análisis...</div>";

            const promptAnalisis = `
            Actúa como experto médico. Analiza el PDF.
            Devuelve HTML limpio. Estructura:
            <h3>🏥 Título y Autores</h3>
            <h3>Objetivo</h3>
            <h3>Metodología</h3>
            <h3>Resultados Clave (Datos en NEGRITA)</h3>
            <h3>Conclusión Clínica</h3>
            `;
            
            // INTENTAMOS LLAMAR CON LA LISTA DE CANDIDATOS
            const htmlAnalisis = await intentarLlamadaRobusta(promptAnalisis);
            
            if(htmlAnalisis) {{
                document.getElementById('analisis-content').innerHTML = marked.parse(htmlAnalisis);
                
                // Si funcionó, usamos el mismo modelo para la infografía
                const promptInfo = `Crea un diagrama 'mermaid graph TD' del estudio. SOLO código.`;
                let codigoMermaid = await llamarGemini(promptInfo, WORKING_MODEL); 
                
                if(codigoMermaid && !codigoMermaid.startsWith("Error")) {{
                    codigoMermaid = codigoMermaid.replace(/```mermaid/g, '').replace(/```/g, '').trim();
                    document.getElementById('infografia-content').innerHTML = `<div class="mermaid">${{codigoMermaid}}</div>`;
                    try {{ mermaid.run(); }} catch(e) {{}}
                }}
                dropZone.innerText = "✅ Listo (Modelo: " + WORKING_MODEL + ")";
            }}
        }}

        // Esta función prueba modelos hasta que uno funcione
        async function intentarLlamadaRobusta(prompt) {{
            let errores = [];
            
            // Si ya sabemos cual funciona, úsalo directo
            if (WORKING_MODEL) {{
                return await llamarGemini(prompt, WORKING_MODEL);
            }}

            // Si no, probamos la lista
            for (let modelo of MODEL_CANDIDATES) {{
                console.log("Probando modelo:", modelo);
                document.getElementById('analisis-content').innerHTML += `<div style='font-size:0.8em; color:grey'>Probando ${modelo}...</div>`;
                
                const resultado = await llamarGemini(prompt, modelo);
                
                if (resultado && !resultado.startsWith("Error")) {{
                    WORKING_MODEL = modelo; // ¡Encontramos uno!
                    return resultado;
                }} else {{
                    errores.push(`${modelo}: ${resultado}`);
                }}
            }}
            
            // Si llegamos aquí, ninguno funcionó
            document.getElementById('analisis-content').innerHTML = 
                `<div class="error-box"><b>FALLO TOTAL: Ningún modelo funcionó.</b><br>Detalles:<br>${errores.join('<br>')}</div>`;
            return null;
        }}

        async function enviarMensaje() {{
            const input = document.getElementById('user-input');
            const txt = input.value;
            if(!txt) return;
            
            const hist = document.getElementById('chat-history');
            hist.innerHTML += `<div class="msg user">${{txt}}</div>`;
            input.value = "";
            
            // Usamos intentarLlamadaRobusta por si acaso el modelo guardado falla
            const respuesta = await intentarLlamadaRobusta(`Responde según el PDF: ${{txt}}`);
            if(respuesta) hist.innerHTML += `<div class="msg ai">${{marked.parse(respuesta)}}</div>`;
            hist.scrollTop = hist.scrollHeight;
        }}

        async function llamarGemini(prompt, modelo) {{
            if(!globalPdfBase64) return "Error: No hay PDF.";
            
            const url = `https://generativelanguage.googleapis.com/v1beta/models/${{modelo}}:generateContent?key=${{API_KEY}}`;
            
            try {{
                const response = await fetch(url, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        contents: [{{
                            parts: [
                                {{ text: prompt }},
                                {{ inline_data: {{ mime_type: "application/pdf", data: globalPdfBase64 }} }}
                            ]
                        }}]
                    }})
                }});
                const data = await response.json();
                
                if(data.error) {{
                    return "Error (" + data.error.code + "): " + data.error.message;
                }}
                return data.candidates[0].content.parts[0].text;
            }} catch (e) {{ 
                return "Error de Red/Fetch"; 
            }}
        }}
    </script>
</body>
</html>
"""

components.html(html_code, height=1000, scrolling=True)
