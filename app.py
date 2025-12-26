import streamlit as st
import streamlit.components.v1 as components

# Configuración de página
st.set_page_config(page_title="Estación Médica IA", layout="wide")

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
    <title>Estación Médica V25 (Pro Poster)</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    </script>
    
    <style>
        /* --- ESTILOS GENERALES UI --- */
        body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f6f9; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
        
        /* BARRA SUPERIOR */
        #drop-zone { background: linear-gradient(90deg, #0d47a1, #1976d2); color: white; padding: 15px; text-align: center; font-weight: 600; cursor: pointer; transition: 0.3s; box-shadow: 0 2px 5px rgba(0,0,0,0.1); letter-spacing: 0.5px; }
        #drop-zone:hover { background: linear-gradient(90deg, #1565c0, #1e88e5); }
        #drop-zone.dragover { background: #4caf50; }
        
        .main-container { display: flex; flex: 1; height: calc(100vh - 60px); }
        
        /* PANEL IZQUIERDO (PDF) */
        .pdf-section { width: 45%; border-right: 1px solid #ddd; background: #323639; display: flex; flex-direction: column; }
        .pdf-toolbar { background: #202124; padding: 10px; display: flex; gap: 10px; justify-content: center; align-items: center; }
        .pdf-scroll-container { flex: 1; overflow: auto; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        .pdf-page-canvas { box-shadow: 0 4px 15px rgba(0,0,0,0.5); margin-bottom: 15px; }

        /* PANEL DERECHO (IA) */
        .right-panel { width: 55%; display: flex; flex-direction: column; background: #fff; }
        .tabs-header { display: flex; background: #f8f9fa; border-bottom: 1px solid #ddd; padding: 0 10px; }
        .tab-btn { flex: 1; padding: 15px; border: none; background: transparent; cursor: pointer; font-weight: 600; color: #5f6368; border-bottom: 3px solid transparent; transition: 0.2s; }
        .tab-btn:hover { color: #1a73e8; background: #f1f3f4; }
        .tab-btn.active { color: #1a73e8; border-bottom: 3px solid #1a73e8; background: white; }
        .tab-content { flex: 1; padding: 25px; overflow-y: auto; display: none; background: #fcfcfc; }
        .tab-content.active { display: block; }

        /* --- ESTILOS DE LA INFOGRAFÍA VISUAL (TIPO PÓSTER) --- */
        /* Este contenedor tiene ancho fijo para asegurar calidad al descargar */
        #infografia-visual-wrapper {
            width: 100%;
            display: flex;
            justify-content: center;
            background: #e9ecef; /* Fondo gris para resaltar el papel */
            padding: 20px;
            box-sizing: border-box;
        }

        #infografia-visual-container {
            width: 800px; /* Ancho fijo A4 aprox para descarga */
            background: white;
            padding: 0; /* El padding lo manejan los hijos */
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
            font-family: 'Roboto', sans-serif;
            color: #333;
            overflow: hidden; /* Para bordes redondeados */
        }

        /* HEADER DEL PÓSTER */
        .poster-header {
            background: #0d47a1; /* Azul Médico Profundo */
            color: white;
            padding: 30px 40px;
            text-align: center;
            border-bottom: 5px solid #f9ab00; /* Toque de color */
        }
        .poster-title { font-size: 28px; font-weight: 900; margin: 0; text-transform: uppercase; letter-spacing: 1px; line-height: 1.2; }
        .poster-subtitle { font-size: 16px; margin-top: 10px; opacity: 0.9; font-weight: 300; }
        .poster-tags { margin-top: 15px; display: flex; gap: 10px; justify-content: center; }
        .poster-tag { background: rgba(255,255,255,0.2); padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; }

        /* BODY DEL PÓSTER */
        .poster-body { padding: 40px; }

        /* SEMÁFORO ESTILIZADO */
        .traffic-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-bottom: 30px; }
        .traffic-card { padding: 15px; border-radius: 8px; border: 1px solid #eee; }
        .card-stop { background: #fff5f5; border-top: 4px solid #d93025; }
        .card-caution { background: #fffbf0; border-top: 4px solid #f9ab00; }
        .card-go { background: #f0f9f4; border-top: 4px solid #188038; }
        
        .traffic-card h3 { margin-top: 0; font-size: 14px; font-weight: 800; text-transform: uppercase; display: flex; align-items: center; gap: 8px; }
        .card-stop h3 { color: #d93025; }
        .card-caution h3 { color: #b06000; }
        .card-go h3 { color: #188038; }
        
        .traffic-card ul { padding-left: 15px; margin: 0; font-size: 13px; color: #444; }
        .traffic-card li { margin-bottom: 4px; }

        /* BIG NUMBERS */
        .numbers-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        .number-card { background: #f8f9fa; padding: 20px; text-align: center; border-radius: 8px; border-left: 5px solid #1976d2; }
        .number-val { display: block; font-size: 32px; font-weight: 900; color: #1976d2; }
        .number-label { font-size: 12px; color: #666; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px; }

        /* FOOTER DEL PÓSTER */
        .poster-footer { background: #263238; color: white; padding: 20px 40px; margin-top: 20px; }
        .poster-footer h3 { margin: 0 0 10px 0; color: #80cbc4; font-size: 16px; text-transform: uppercase; }
        .poster-footer ul { padding-left: 20px; margin: 0; font-size: 14px; color: #cfd8dc; }
        
        /* DIAGRAMA MERMAID DENTRO DEL PÓSTER */
        .poster-mermaid { margin-top: 30px; border-top: 2px dashed #eee; padding-top: 20px; }
        .poster-mermaid h3 { text-align: center; color: #555; font-size: 14px; text-transform: uppercase; }

        /* BOTONES */
        button { cursor: pointer; padding: 8px 16px; border-radius: 4px; border: none; font-weight: 600; font-size: 13px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .btn-zoom { background: white; color: #333; }
        .btn-pdf { background: #e53935; color: white; text-decoration: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; display: none; }
        .btn-img { background: #00897b; color: white; margin-left: 10px; display: none; }
        .btn-img:hover { background: #00796b; }

        /* Markdown Texto Normal */
        .markdown-body { font-size: 15px; line-height: 1.6; color: #333; }
        .markdown-body h2 { color: #1565c0; border-bottom: 2px solid #eee; margin-top: 30px; }
        .markdown-body strong { color: #c62828; }

        /* Chat */
        #chat-history { height: 85%; overflow-y: auto; padding: 10px; }
        .msg { padding: 10px 15px; border-radius: 10px; margin-bottom: 10px; font-size: 14px; max-width: 85%; }
        .msg.user { background: #e3f2fd; color: #1565c0; align-self: flex-end; margin-left: auto; }
        .msg.ai { background: #f5f5f5; color: #333; border: 1px solid #ddd; }
    </style>
</head>
<body>

    <div id="drop-zone">📄 ARRASTRA GPC (V25: Póster Médico Pro)</div>

    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button class="btn-zoom" onclick="ajustarZoom(-0.2)">➖</button>
                <span id="zoom-level" style="color:white; font-size:12px; margin:0 10px;">100%</span>
                <button class="btn-zoom" onclick="ajustarZoom(0.2)">➕</button>
                <a id="btn-download" class="btn-pdf">⬇️ PDF</a>
                <button id="btn-img-dl" class="btn-img" onclick="descargarPoster()">📸 Descargar Infografía</button>
            </div>
            <div id="pdf-container" class="pdf-scroll-container"></div>
        </div>

        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="abrirPestana('tab-analisis')">📝 Análisis</button>
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">🎨 Infografía (Póster)</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">💬 Chat</button>
            </div>
            
            <div id="tab-analisis" class="tab-content active">
                <div id="analisis-content" class="markdown-body">
                    <div style="text-align:center; margin-top:60px; color:#999;">
                        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                        <br><br>Sube una guía clínica para analizarla.
                    </div>
                </div>
            </div>

            <div id="tab-infografia" class="tab-content">
                <div id="infografia-visual-wrapper">
                    <div id="infografia-visual-container">
                        <div style="padding:50px; text-align:center; color:#999;">
                            El póster visual aparecerá aquí tras el análisis.
                        </div>
                    </div>
                </div>
            </div>

            <div id="tab-chat" class="tab-content">
                <div id="chat-history"></div>
                <div style="padding:10px; border-top:1px solid #eee; display:flex; gap:10px;">
                    <input type="text" id="user-input" placeholder="Pregunta..." style="flex:1; padding:10px; border:1px solid #ddd; border-radius:20px; outline:none;" onkeypress="if(event.key==='Enter') enviarMensaje()">
                    <button onclick="enviarMensaje()" style="background:#1976d2; color:white;">Enviar</button>
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
            
            // Botón descarga solo en pestaña infografía y si hay contenido
            const btn = document.getElementById('btn-img-dl');
            const hasContent = document.querySelector('.poster-title');
            if(id === 'tab-infografia' && hasContent) {
                btn.style.display = 'inline-block';
            } else {
                btn.style.display = 'none';
            }
            
            // Highlight tabs
            if(id.includes('analisis')) document.querySelectorAll('.tab-btn')[0].classList.add('active');
            if(id.includes('infografia')) document.querySelectorAll('.tab-btn')[1].classList.add('active');
            if(id.includes('chat')) document.querySelectorAll('.tab-btn')[2].classList.add('active');
        }

        // --- DESCARGA HQ ---
        function descargarPoster() {
            const element = document.getElementById('infografia-visual-container');
            // Forzamos opciones para mejorar calidad de texto
            html2canvas(element, { 
                scale: 2.5, // Super alta resolución
                useCORS: true,
                backgroundColor: "#ffffff"
            }).then(canvas => {
                const link = document.createElement('a');
                link.download = 'Infografia_Medica_Pro.png';
                link.href = canvas.toDataURL('image/png');
                link.click();
            });
        }

        // --- PDF LOGIC ---
        const dropZone = document.getElementById('drop-zone');
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
        dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('dragover'); });
        dropZone.addEventListener('drop', async (e) => {
            e.preventDefault(); dropZone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if(file && file.type === "application/pdf") {
                dropZone.innerHTML = "⏳ Analizando Evidencia...";
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

        function limpiarCodigo(t) {
            // Elimina bloques markdown y texto conversacional
            let s = t.replace(/```html|```/gi, "").trim();
            // Si la IA añade texto antes del primer div, lo borramos
            const primerDiv = s.indexOf("<div");
            if(primerDiv > -1) s = s.substring(primerDiv);
            return s;
        }

        function limpiarMermaid(t) {
            let s = t.replace(/```mermaid|```/gi, "").trim();
            const idx = s.indexOf("graph TD");
            if(idx > -1) s = s.substring(idx);
            return s;
        }

        async function procesarIA() {
            // 1. ANÁLISIS TÉCNICO (Markdown)
            dropZone.innerText = "🤖 Fase 1: Extracción de Datos...";
            const promptAnalisis = `
            Actúa como analista técnico médico. Sin saludos. Sin introducción.
            Analiza el PDF y extrae: Definiciones, Algoritmo Agudo (Metas/Dosis), Soporte Vital, Semáforo Evidencia, Poblaciones.
            Formato: Markdown técnico.
            `;
            let res1 = await llamarIA(promptAnalisis);
            if(res1) document.getElementById('analisis-content').innerHTML = marked.parse(res1);

            // 2. INFOGRAFÍA PÓSTER (HTML Estricto)
            dropZone.innerText = "🎨 Fase 2: Generando Póster...";
            const containerPoster = document.getElementById('infografia-visual-container');
            containerPoster.innerHTML = "<div style='padding:40px; text-align:center;'>🎨 Diseñando layout gráfico...</div>";

            const promptPoster = `
            Eres un motor de renderizado HTML. Tu tarea es convertir los datos médicos del PDF en código HTML limpio para un póster.
            
            REGLAS ESTRICTAS:
            1. NO hables. NO saludes. NO digas "Aquí tienes el código".
            2. Devuelve SOLO una cadena de HTML válida.
            3. Usa EXACTAMENTE esta estructura de clases (ya tienen CSS definido):

            <div class="poster-header">
                <h1 class="poster-title">TITULO CLÍNICO CORTO</h1>
                <div class="poster-tags"><span class="poster-tag">AÑO</span> <span class="poster-tag">SOCIEDAD</span></div>
                <p class="poster-subtitle">Objetivo Principal</p>
            </div>

            <div class="poster-body">
                <div class="traffic-grid">
                    <div class="traffic-card card-stop">
                        <h3>⛔ STOP (No hacer)</h3>
                        <ul><li>Práctica 1</li><li>Práctica 2</li></ul>
                    </div>
                    <div class="traffic-card card-caution">
                        <h3>⚠️ PRECAUCIÓN</h3>
                        <ul><li>Duda 1</li><li>Duda 2</li></ul>
                    </div>
                    <div class="traffic-card card-go">
                        <h3>✅ GO (Estándar)</h3>
                        <ul><li>Rec. Fuerte 1</li><li>Rec. Fuerte 2</li></ul>
                    </div>
                </div>

                <div class="numbers-grid">
                    <div class="number-card">
                        <span class="number-val">CIFRA 1</span>
                        <span class="number-label">Unidad/Contexto</span>
                    </div>
                    <div class="number-card">
                        <span class="number-val">CIFRA 2</span>
                        <span class="number-label">Unidad/Contexto</span>
                    </div>
                </div>

                <div id="mermaid-placeholder" class="poster-mermaid"></div>
            </div>

            <div class="poster-footer">
                <h3>TAKE HOME MESSAGES</h3>
                <ul><li>Mensaje 1</li><li>Mensaje 2</li></ul>
            </div>
            `;
            
            let htmlCode = await llamarIA(promptPoster);
            
            if(htmlCode) {
                // Limpiamos cualquier "basura" que la IA haya puesto antes del HTML
                htmlCode = limpiarCodigo(htmlCode);
                containerPoster.innerHTML = htmlCode;

                // 3. GRÁFICO MERMAID
                const mermaidDiv = document.getElementById('mermaid-placeholder');
                if(mermaidDiv) {
                    mermaidDiv.innerHTML = "<h3>Algoritmo de Flujo</h3><div id='mermaid-graph'>Generando...</div>";
                    const promptMermaid = `
                    Crea un diagrama 'mermaid graph TD' MUY SIMPLE (max 8 nodos) del manejo agudo.
                    REGLAS:
                    1. SOLO código. Sin texto extra.
                    2. Usa IDs cortos: A, B, C...
                    3. TEXTOS SIEMPRE ENTRE COMILLAS: A["Texto"] --> B["Texto"]
                    `;
                    let mermaidCode = await llamarIA(promptMermaid);
                    if(mermaidCode) {
                        const cleanM = limpiarMermaid(mermaidCode);
                        document.getElementById('mermaid-graph').innerHTML = `<div class="mermaid">${cleanM}</div>`;
                        try { mermaid.run(); } catch(e){}
                    }
                }
                
                dropZone.innerText = "✅ Proceso Finalizado";
                if(document.getElementById('tab-infografia').classList.contains('active')) {
                    document.getElementById('btn-img-dl').style.display = 'inline-block';
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

        async function enviarMensaje() {
            const i = document.getElementById('user-input');
            const h = document.getElementById('chat-history');
            const t = i.value; if(!t) return;
            h.innerHTML += `<div class="msg user">${t}</div>`; i.value="";
            const res = await llamarIA(`Respuesta técnica breve: ${t}`);
            h.innerHTML += `<div class="msg ai">${res ? marked.parse(res) : "Error"}</div>`;
        }
    </script>
</body>
</html>
"""

final_html = html_template.replace("__API_KEY_PLACEHOLDER__", API_KEY)
components.html(final_html, height=1000, scrolling=True)
