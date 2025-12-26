import streamlit as st
import streamlit.components.v1 as components

# Configuración de página: ANCHO COMPLETO REAL
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
    <title>Estación Médica V26</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script src="https://html2canvas.hertzen.com/dist/html2canvas.min.js"></script>
    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    </script>
    
    <style>
        /* --- LAYOUT GLOBAL (ANCHO COMPLETO RECUPERADO) --- */
        body { margin: 0; padding: 0; background-color: #f4f6f9; height: 100vh; display: flex; flex-direction: column; overflow: hidden; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        
        .main-container { display: flex; width: 100vw; height: 100vh; }
        
        /* IZQUIERDA: VISOR PDF (50% ANCHO) */
        .pdf-section { width: 50%; min-width: 50%; border-right: 1px solid #ddd; background: #525659; display: flex; flex-direction: column; }
        .pdf-toolbar { background: #333; padding: 10px; display: flex; gap: 10px; justify-content: center; align-items: center; color: white; }
        .pdf-scroll-container { flex: 1; overflow: auto; display: flex; flex-direction: column; align-items: center; padding: 20px; }
        .pdf-page-canvas { box-shadow: 0 4px 10px rgba(0,0,0,0.5); margin-bottom: 15px; }

        /* DERECHA: PANELES IA (50% ANCHO) */
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
        .markdown-body h3 { font-size: 16px; font-weight: 700; color: #555; text-transform: uppercase; margin-top: 20px; }
        .markdown-body strong { color: #d32f2f; background: rgba(211, 47, 47, 0.05); padding: 0 4px; border-radius: 3px; }
        .markdown-body ul { padding-left: 20px; }
        .markdown-body li { margin-bottom: 8px; }

        /* --- ESTILOS DE LA INFOGRAFÍA VISUAL (PÓSTER MEJORADO) --- */
        #infografia-wrapper {
            background: #e9ecef;
            padding: 40px;
            display: flex;
            justify-content: center;
            min-height: 100%;
        }

        #infografia-visual-container {
            width: 800px; /* Ancho fijo para exportación perfecta */
            background: white;
            box-shadow: 0 20px 50px rgba(0,0,0,0.15);
            font-family: 'Roboto', 'Segoe UI', sans-serif;
            color: #333;
            position: relative;
            overflow: hidden;
            border-radius: 4px; /* Ligero borde */
        }

        /* Header Moderno */
        .poster-header {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); /* Degradado Profundo */
            color: white;
            padding: 40px;
            text-align: center;
            position: relative;
        }
        .poster-header::after { content: ""; display: block; width: 60px; height: 4px; background: #4db6ac; margin: 20px auto 0; }
        .poster-title { font-size: 32px; font-weight: 900; margin: 0; line-height: 1.1; letter-spacing: -0.5px; }
        .poster-meta { margin-top: 15px; font-size: 14px; opacity: 0.8; font-weight: 300; text-transform: uppercase; letter-spacing: 1px; }

        .poster-body { padding: 40px; }

        /* Tarjetas de Semáforo */
        .traffic-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 40px; }
        .t-card { background: #f8f9fa; border-radius: 12px; padding: 20px; position: relative; overflow: hidden; border: 1px solid #eee; }
        .t-card h3 { margin: 0 0 15px 0; font-size: 14px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.5px; display: flex; align-items: center; gap: 8px; }
        .t-card ul { padding-left: 15px; margin: 0; font-size: 13px; color: #555; line-height: 1.5; }
        .t-card li { margin-bottom: 6px; }
        
        /* Colores semáforo */
        .tc-stop { border-top: 6px solid #e53935; } .tc-stop h3 { color: #c62828; }
        .tc-wait { border-top: 6px solid #fbc02d; } .tc-wait h3 { color: #f57f17; }
        .tc-go   { border-top: 6px solid #43a047; } .tc-go h3   { color: #2e7d32; }

        /* Cifras Clave (Big Numbers) */
        .big-nums { display: flex; gap: 20px; justify-content: center; margin-bottom: 40px; background: #fff; padding: 20px 0; border-top: 1px dashed #ddd; border-bottom: 1px dashed #ddd; }
        .bn-item { text-align: center; flex: 1; border-right: 1px solid #eee; }
        .bn-item:last-child { border: none; }
        .bn-val { display: block; font-size: 36px; font-weight: 800; color: #2c5364; }
        .bn-lbl { font-size: 11px; text-transform: uppercase; color: #888; font-weight: 700; letter-spacing: 1px; margin-top: 5px; }

        /* Footer */
        .poster-footer { background: #f1f8e9; padding: 30px 40px; border-radius: 12px; border: 1px solid #dcedc8; }
        .poster-footer h3 { margin: 0 0 10px 0; color: #558b2f; font-size: 14px; text-transform: uppercase; font-weight: 800; }
        .poster-footer ul { margin: 0; padding-left: 20px; color: #33691e; font-size: 14px; }

        /* Diagrama */
        .poster-mermaid { margin-top: 40px; text-align: center; }
        .poster-mermaid h4 { font-size: 12px; color: #999; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 20px; }

        /* BOTONES UI */
        button { cursor: pointer; padding: 8px 16px; border-radius: 4px; border: none; font-weight: 600; font-size: 13px; box-shadow: 0 1px 3px rgba(0,0,0,0.2); transition: 0.2s; }
        button:hover { transform: translateY(-1px); }
        .btn-zoom { background: white; color: #333; }
        .btn-pdf { background: #e53935; color: white; text-decoration: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; display: none; }
        .btn-action { background: #00897b; color: white; display: none; margin-left: 10px; }
        .btn-action:hover { background: #00796b; }

        /* CHAT */
        #chat-history { padding: 20px; height: calc(100% - 70px); overflow-y: auto; }
        .msg { padding: 12px 16px; border-radius: 12px; margin-bottom: 12px; font-size: 14px; max-width: 85%; line-height: 1.5; }
        .msg.user { background: #e3f2fd; color: #1565c0; align-self: flex-end; border-bottom-right-radius: 2px; }
        .msg.ai { background: #f5f5f5; color: #333; border: 1px solid #eee; align-self: flex-start; border-bottom-left-radius: 2px; }
        .chat-input { padding: 15px; border-top: 1px solid #eee; display: flex; gap: 10px; background: white; }
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
                <div style="font-size:40px; margin-bottom:10px;">📄</div>
                <div style="font-weight:bold;">ARRASTRA TU GUÍA CLÍNICA AQUÍ</div>
                <div style="font-size:12px; margin-top:5px;">Análisis Profundo + Infografía Visual</div>
            </div>
            
            <div id="pdf-container" class="pdf-scroll-container" style="display:none;"></div>
        </div>

        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="abrirPestana('tab-analisis')">📝 Análisis Profundo</button>
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">🎨 Infografía Visual</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">💬 Chat</button>
                <button id="btn-save-img" class="btn-action" onclick="descargarPoster()">📸 Descargar Imagen</button>
            </div>
            
            <div id="tab-analisis" class="tab-content active">
                <div class="content-padding">
                    <div id="analisis-content" class="markdown-body">
                        <div style="text-align:center; margin-top:80px; color:#aaa;">
                            Esperando documento...
                        </div>
                    </div>
                </div>
            </div>

            <div id="tab-infografia" class="tab-content">
                <div id="infografia-wrapper">
                    <div id="infografia-visual-container">
                        <div style="padding:60px; text-align:center; color:#999;">
                            El póster se generará aquí automáticamente.
                        </div>
                    </div>
                </div>
            </div>

            <div id="tab-chat" class="tab-content">
                <div id="chat-history"></div>
                <div class="chat-input">
                    <input type="text" id="user-input" placeholder="Pregunta técnica..." style="flex:1; padding:10px; border:1px solid #ddd; border-radius:4px; outline:none;" onkeypress="if(event.key==='Enter') enviarMensaje()">
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

        // --- GESTIÓN DE UI ---
        function abrirPestana(id) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            
            // Lógica botones header
            const btn = document.getElementById('btn-save-img');
            const hasContent = document.querySelector('.poster-title'); // Si ya se generó el título
            
            if(id === 'tab-infografia' && hasContent) {
                btn.style.display = 'block';
            } else {
                btn.style.display = 'none';
            }
            
            // Activar visualmente la pestaña
            if(id.includes('analisis')) document.querySelectorAll('.tab-btn')[0].classList.add('active');
            if(id.includes('infografia')) document.querySelectorAll('.tab-btn')[1].classList.add('active');
            if(id.includes('chat')) document.querySelectorAll('.tab-btn')[2].classList.add('active');
        }

        // --- PDF DRAG & DROP ---
        const dropZone = document.getElementById('drop-zone');
        // El dropzone ahora es toda el área izquierda si está vacía, o un overlay
        
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.style.background = "#333"; });
        dropZone.addEventListener('dragleave', () => { dropZone.style.background = "transparent"; });
        
        dropZone.addEventListener('drop', async (e) => {
            e.preventDefault();
            const file = e.dataTransfer.files[0];
            if(file && file.type === "application/pdf") {
                // UI Update
                dropZone.style.display = "none";
                document.getElementById('pdf-container').style.display = "flex";
                document.getElementById('analisis-content').innerHTML = "<div style='text-align:center; margin-top:50px;'>⏳ <b>Analizando Guía Clínica...</b><br>Extrayendo evidencia, dosis y algoritmos.</div>";
                
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

        // --- CEREBRO IA ---
        async function procesarIA() {
            // 1. ANÁLISIS PROFUNDO (Markdown Técnico)
            // Restauramos el prompt "Jefe de Servicio" pero con tono neutro
            const promptAnalisis = `
            Actúa como un Sistema Experto en Medicina Intensiva. 
            Realiza una disección técnica exhaustiva de la Guía de Práctica Clínica proporcionada.
            
            ESTRUCTURA DE SALIDA (MARKDOWN):
            1. **Definiciones y Nuevos Criterios:** Cambios en definiciones, scores, fenotipos.
            2. **Algoritmo de Manejo Agudo (Resucitación):** Metas hemodinámicas (Targets), Primera Línea, Dosis exactas.
            3. **Soporte Vital y Procedimientos:** Ventilación, Hemodinámica, ECMO/Rescate.
            4. **Semáforo de Evidencia:** STOP (Rojo), Áreas Grises (Amarillo), Nuevos Estándares (Verde).
            5. **Poblaciones Especiales:** Renal, Obesidad, etc.
            
            TONO: Estrictamente técnico, directo, sin saludos. Usa negritas para cifras y fármacos.
            `;
            
            let resAnalisis = await llamarIA(promptAnalisis);
            if(resAnalisis) {
                document.getElementById('analisis-content').innerHTML = marked.parse(limpiarTexto(resAnalisis));
            }

            // 2. INFOGRAFÍA VISUAL (HTML Estructurado para el Póster)
            const promptPoster = `
            Actúa como Diseñador Gráfico Médico. Genera el código HTML para un PÓSTER CIENTÍFICO basado en la guía.
            
            Reglas:
            1. NO uses Markdown. Devuelve SOLO código HTML.
            2. NO incluyas explicaciones.
            3. Usa EXACTAMENTE esta estructura de clases CSS (ya definidas):

            <div class="poster-header">
                <h1 class="poster-title">TITULO BREVE DE LA GUÍA</h1>
                <div class="poster-meta">SOCIEDAD • AÑO • POBLACIÓN DIANA</div>
            </div>

            <div class="poster-body">
                <div class="traffic-grid">
                    <div class="t-card tc-stop">
                        <h3>⛔ STOP (No hacer)</h3>
                        <ul><li>Práctica desaconsejada 1</li><li>Práctica desaconsejada 2</li></ul>
                    </div>
                    <div class="t-card tc-wait">
                        <h3>⚠️ PRECAUCIÓN</h3>
                        <ul><li>Individualizar 1</li><li>Duda 2</li></ul>
                    </div>
                    <div class="t-card tc-go">
                        <h3>✅ GO (Recomendado)</h3>
                        <ul><li>Estándar 1</li><li>Estándar 2</li></ul>
                    </div>
                </div>

                <div class="big-nums">
                    <div class="bn-item">
                        <span class="bn-val">DATOS</span>
                        <span class="bn-lbl">DOSIS/META</span>
                    </div>
                    <div class="bn-item">
                        <span class="bn-val">CIFRA</span>
                        <span class="bn-lbl">TIEMPO/UMBRAL</span>
                    </div>
                     <div class="bn-item">
                        <span class="bn-val">VALOR</span>
                        <span class="bn-lbl">TARGET</span>
                    </div>
                </div>

                <div class="poster-mermaid" id="mermaid-target">
                    <h4>Algoritmo Simplificado</h4>
                    <div id="mermaid-loading">Generando gráfico...</div>
                </div>
            </div>

            <div class="poster-footer">
                <h3>TAKE HOME MESSAGES</h3>
                <ul>
                    <li>Mensaje clave 1.</li>
                    <li>Mensaje clave 2.</li>
                </ul>
            </div>
            `;
            
            let htmlPoster = await llamarIA(promptPoster);
            if(htmlPoster) {
                document.getElementById('infografia-visual-container').innerHTML = limpiarTexto(htmlPoster);
                
                // 3. GRÁFICO MERMAID (Insertado dentro del póster)
                const promptMermaid = `
                Crea un diagrama 'mermaid graph TD' MUY SIMPLE (max 8-10 nodos) del manejo agudo.
                REGLAS CRÍTICAS PARA EVITAR ERRORES:
                1. Usa SOLO 'graph TD'.
                2. IDs cortos (A, B, C...).
                3. TEXTOS SIEMPRE ENTRE COMILLAS DOBLES: A["Texto Médico"] --> B["Otro Texto"]
                4. NO uses paréntesis () ni corchetes [] DENTRO de las comillas.
                5. SOLO devuelve el código.
                `;
                
                let mermaidCode = await llamarIA(promptMermaid);
                if(mermaidCode) {
                    const cleanM = limpiarMermaid(mermaidCode);
                    const target = document.getElementById('mermaid-loading');
                    if(target) {
                        target.innerHTML = `<div class="mermaid">${cleanM}</div>`;
                        try { mermaid.run(); } catch(e){}
                    }
                }
                
                // Mostrar botón de descarga si estamos en la pestaña
                if(document.getElementById('tab-infografia').classList.contains('active')) {
                    document.getElementById('btn-save-img').style.display = 'block';
                }
            }
        }

        // --- UTILIDADES IA ---
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

        function limpiarTexto(t) {
            // Elimina markdown blocks ```html ... ```
            return t.replace(/```html|```/gi, "").trim();
        }
        
        function limpiarMermaid(t) {
            let s = t.replace(/```mermaid|```/gi, "").trim();
            const idx = s.indexOf("graph TD");
            if(idx > -1) s = s.substring(idx);
            return s;
        }

        // --- CHAT ---
        async function enviarMensaje() {
            const i = document.getElementById('user-input');
            const h = document.getElementById('chat-history');
            const t = i.value; if(!t) return;
            
            h.innerHTML += `<div class="msg user">${t}</div>`; 
            i.value = ""; 
            h.scrollTop = h.scrollHeight;
            
            const res = await llamarIA(`Respuesta técnica muy breve sobre la guía: ${t}`);
            h.innerHTML += `<div class="msg ai">${res ? marked.parse(limpiarTexto(res)) : "Error"}</div>`;
            h.scrollTop = h.scrollHeight;
        }
        
        // --- DESCARGA IMAGEN ---
        function descargarPoster() {
            const element = document.getElementById('infografia-visual-container');
            html2canvas(element, { scale: 2.5, backgroundColor: "#ffffff" }).then(canvas => {
                const link = document.createElement('a');
                link.download = 'Infografia_Medica.png';
                link.href = canvas.toDataURL('image/png');
                link.click();
            });
        }
    </script>
</body>
</html>
"""

final_html = html_template.replace("__API_KEY_PLACEHOLDER__", API_KEY)
components.html(final_html, height=1000, scrolling=True)
