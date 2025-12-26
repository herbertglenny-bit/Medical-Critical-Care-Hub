¡Cambio de rumbo recibido! Pasamos de una "Clase para Residentes" (PowerPoint) a un "Análisis Técnico de Alta Complejidad" (Jefe de Servicio).

Este nuevo prompt es mucho más potente para uso clínico real, ya que busca dosis, targets hemodinámicos y semáforos de evidencia.

Aquí tienes la Versión 18 (Jefe de Servicio UCI). He actualizado el código para que la IA siga estrictamente tu nueva estructura de 6 puntos.

Instrucciones:
Ve a app.py.

Borra todo.

Pega el código. (La seguridad sigue intacta, no toques los Secrets).

Python

import streamlit as st
import streamlit.components.v1 as components

# Configuración de página
st.set_page_config(page_title="Estación Médica IA", layout="wide")

# --- SEGURIDAD: LEEMOS LA CLAVE DESDE LOS SECRETOS ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except (FileNotFoundError, KeyError):
    st.error("⚠️ Error: No encuentro 'GEMINI_API_KEY' en los Secrets de Streamlit.")
    st.stop()
# -----------------------------------------------------

html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Estación Médica V18 (Jefe de Servicio)</title>
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
        
        /* LAYOUT */
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

        /* Estilos Markdown Clínico */
        .markdown-body { line-height: 1.6; color: #333; font-size: 0.95rem; }
        .markdown-body h1, .markdown-body h2 { color: #1a73e8; border-bottom: 2px solid #eee; margin-top: 25px; padding-bottom: 5px; }
        .markdown-body h3 { color: #202124; font-weight: bold; margin-top: 20px; text-transform: uppercase; font-size: 0.9rem; letter-spacing: 0.5px; }
        .markdown-body ul { padding-left: 20px; }
        .markdown-body li { margin-bottom: 6px; }
        .markdown-body strong { color: #d93025; font-weight: 700; } /* Datos críticos en rojo */
        .markdown-body blockquote { border-left: 4px solid #1a73e8; padding-left: 10px; color: #555; background: #f8f9fa; }

        /* Chat */
        #chat-container { display: flex; flex-direction: column; height: 100%; }
        #chat-history { flex: 1; overflow-y: auto; margin-bottom: 10px; }
        .msg { margin-bottom: 10px; padding: 10px; border-radius: 10px; max-width: 85%; }
        .msg.user { background: #e8f0fe; align-self: flex-end; }
        .msg.ai { background: #f1f3f4; align-self: flex-start; }
        .chat-input-area { display: flex; gap: 10px; padding-top: 10px; border-top: 1px solid #eee; }
        #user-input { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 20px; }

        /* Botones */
        button { cursor: pointer; padding: 6px 12px; border-radius: 4px; border: none; background: white; font-weight: bold; }
        .btn-download { background-color: #4CAF50; color: white; text-decoration: none; padding: 6px 12px; border-radius: 4px; font-size: 14px; display: none; }
    </style>
</head>
<body>

    <div id="drop-zone">📄 ARRASTRA GPC (Modo: Jefe de Servicio)</div>

    <div class="main-container">
        <div class="pdf-section">
            <div class="pdf-toolbar">
                <button onclick="ajustarZoom(-0.2)">➖ Zoom</button>
                <span id="zoom-level" style="min-width: 50px; text-align: center;">100%</span>
                <button onclick="ajustarZoom(0.2)">➕ Zoom</button>
                <button onclick="rotarPDF()">🔄 Rotar</button>
                <a id="btn-download" class="btn-download" download="documento.pdf" style="margin-left: 10px;">⬇️ Descargar</a>
            </div>
            <div id="pdf-container" class="pdf-scroll-container"></div>
        </div>

        <div class="right-panel">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="abrirPestana('tab-analisis')">📝 Análisis Avanzado</button>
                <button class="tab-btn" onclick="abrirPestana('tab-infografia')">📊 Algoritmo</button>
                <button class="tab-btn" onclick="abrirPestana('tab-chat')">💬 Discusión</button>
            </div>
            
            <div id="tab-analisis" class="tab-content active">
                <div id="analisis-content" class="markdown-body">
                    <p style="color:#666; text-align:center; margin-top:50px;">
                        Sistema listo.<br>Sube una Guía de Práctica Clínica para disección técnica.
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
                        <input type="text" id="user-input" placeholder="Consultar detalle técnico..." onkeypress="if(event.key==='Enter') enviarMensaje()">
                        <button onclick="enviarMensaje()">Enviar</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_KEY = "__API_KEY_PLACEHOLDER__"; 

        const MODEL_CANDIDATES = [
            "gemini-2.0-flash", 
            "gemini-2.5-flash", 
            "gemini-1.5-pro",
            "gemini-flash-latest"
        ];
        let WORKING_MODEL = null;

        let pdfDoc = null, scale = 1.0, rotation = 0, globalPdfBase64 = null;
        mermaid.initialize({ startOnLoad: false, theme: 'neutral' });

        function abrirPestana(id) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
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
                dropZone.innerText = "⏳ Diseccionando evidencia...";
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

        // --- LIMPIEZA DE CÓDIGO ---
        function limpiarMarkdown(texto) {
            let limpio = texto.replace(/```html/gi, "").replace(/```/g, "");
            limpio = limpio.replace(/<!DOCTYPE html>/gi, "").replace(/<html>/gi, "").replace(/<\/html>/gi, "");
            limpio = limpio.replace(/<head>[\s\S]*?<\/head>/gi, "").replace(/<body>/gi, "").replace(/<\/body>/gi, "");
            return limpio.trim();
        }

        function limpiarMermaid(texto) {
            let limpio = texto.replace(/```mermaid/gi, "").replace(/```/g, "");
            const indiceInicio = limpio.indexOf("graph TD");
            if (indiceInicio !== -1) limpio = limpio.substring(indiceInicio);
            return limpio.trim();
        }

        async function procesarIA() {
            dropZone.innerText = "🤖 Análisis Jefe Servicio...";
            document.getElementById('analisis-content').innerHTML = "<div class='msg ai'>🧠 <b>Iniciando disección profunda...</b><br>Extrayendo targets hemodinámicos, dosis y semáforos de evidencia...</div>";
            
            // --- NUEVO PROMPT TÉCNICO AVANZADO ---
            const prompt = `
            # ROL
            Actúa como un Jefe de Servicio de Medicina Intensiva con subespecialización en Medicina Basada en la Evidencia. Tu objetivo es realizar una disección exhaustiva y detallada de la Guía de Práctica Clínica (GPC) proporcionada.

            # OBJETIVO
            Generar un **Resumen Clínico Avanzado** dirigido exclusivamente a médicos especialistas en Cuidados Intensivos. El resumen debe ser extremadamente detallado, técnico y orientado a la resolución de problemas clínicos complejos a pie de cama. Ignora introducciones genéricas o epidemiología básica.

            # ESTRUCTURA OBLIGATORIA DEL ANÁLISIS
            Por favor, analiza el documento y estructura la respuesta en los siguientes módulos clínicos, usando formato MARKDOWN limpio:

            ## 1. Definiciones, Criterios y Fenotipos
            * **Nuevos Criterios Diagnósticos:** ¿Han cambiado los umbrales o definiciones (ej. Sepsis-3, Berlín, EOLIA)?
            * **Fenotipos/Subgrupos:** ¿Distingue la guía subgrupos de pacientes que requieran manejo diferenciado (ej. fenotipos inflamatorios, pacientes inmunodeprimidos)?
            * **Scores y Escalas:** ¿Qué escalas de gravedad o pronóstico recomienda calcular explícitamente?

            ## 2. Algoritmo de Manejo en Fase Aguda (Resucitación)
            * **Metas ("Targets") Inmediatas:** Lista detallada de objetivos hemodinámicos (TAM, Lactato), respiratorios (SpO2, pH, Driving Pressure) o metabólicos.
            * **Primera Línea de Tratamiento:** Fármacos o intervenciones "Gold Standard" para las primeras 6 horas.
            * **Dosis y Posología:** Extrae tablas de dosificación, ajustes por función renal/hepática y tiempos de infusión si aparecen en el texto.

            ## 3. Soporte Vital y Procedimientos (El "Core" de UCI)
            * **Soporte Ventilatorio:** Modos recomendados, titulación de PEEP, volumen corriente, indicaciones de prono o bloqueo neuromuscular.
            * **Soporte Hemodinámico:** Elección de vasopresores/inotrópicos (primera vs. segunda línea), tipos de fluidos y monitorización.
            * **Terapias de Rescate/ECMO:** Criterios exactos de indicación y contraindicación para terapias extracorpóreas o avanzadas.

            ## 4. Semáforo de Evidencia (Cambios de Práctica)
            * 🔴 **STOP (No hacer):** Intervenciones que la guía desaconseja explícitamente o que han demostrado daño (muy importante).
            * 🟡 **Áreas Grises:** Situaciones donde la evidencia es débil y la guía sugiere "individualizar" o "considerar".
            * 🟢 **GO (Nuevos Estándares):** Recomendaciones fuertes que cambian la práctica habitual previa.

            ## 5. Poblaciones Especiales en UCI
            * Detalla recomendaciones específicas para: Pacientes con Fallo Renal (CRRT), Obesidad Mórbida, Anciano frágil, Embarazo o Inmunosupresión si la guía los menciona.

            ## 6. Criterios de Ingreso y Alta
            * Criterios de admisión en UCI recomendados.
            * Criterios de "weaning" o desescalada terapéutica.
            * Limitación del Esfuerzo Terapéutico (LET): ¿Menciona la guía aspectos éticos o de pronóstico fútil específicos para esta patología?

            ---
            **Instrucciones de Estilo:**
            * Usa lenguaje técnico médico preciso.
            * Usa **negritas** para resaltar cifras, umbrales (ej. **< 6 ml/kg**) y fármacos.
            * Si la guía incluye tablas o algoritmos visuales importantes, indica: *"[Ver Tabla/Figura X del documento original]"* y resume su contenido.
            * Cita las fuentes o páginas de donde extraes los datos críticos.
            `;
            
            let respuestaRaw = await intentarLlamadaRobusta(prompt);
            
            if(respuestaRaw) {
                const textoLimpio = limpiarMarkdown(respuestaRaw);
                document.getElementById('analisis-content').innerHTML = marked.parse(textoLimpio);
                
                // Infografía - Pedimos un árbol de decisión clínico
                document.getElementById('infografia-content').innerHTML = "<div class='msg ai'>Diseñando árbol de decisión clínico...</div>";
                let mermaidRaw = await llamarGemini(`Crea un diagrama de flujo 'mermaid graph TD' detallado sobre el Algoritmo de Manejo Agudo. Usa rombos para decisiones clínicas críticas (ej. ¿TAM < 65? ¿Responde a fluidos?). SOLO CÓDIGO.`, WORKING_MODEL);
                
                if(mermaidRaw && !mermaidRaw.startsWith("Error")) {
                    const mermaidClean = limpiarMermaid(mermaidRaw);
                    document.getElementById('infografia-content').innerHTML = `<div class="mermaid">${mermaidClean}</div>`;
                    try { mermaid.run(); } catch(e) { 
                        document.getElementById('infografia-content').innerHTML += "<br><small style='color:red'>Error visualizando gráfico</small>";
                    }
                }
                dropZone.innerText = "✅ Análisis Completado";
            }
        }

        async function intentarLlamadaRobusta(prompt) {
            if (WORKING_MODEL) return await llamarGemini(prompt, WORKING_MODEL);
            let errores = [];
            for (let modelo of MODEL_CANDIDATES) {
                console.log(`Probando ${modelo}...`);
                const res = await llamarGemini(prompt, modelo);
                if (res && !res.startsWith("Error")) {
                    WORKING_MODEL = modelo;
                    return res;
                }
                errores.push(`${modelo}: ${res}`);
            }
            document.getElementById('analisis-content').innerHTML = `<div class="error-box"><b>Fallo.</b><br>${errores.join('<br>')}</div>`;
            return null;
        }

        async function enviarMensaje() {
            const i = document.getElementById('user-input');
            const t = i.value; if(!t) return;
            const h = document.getElementById('chat-history');
            
            h.innerHTML += `<div class="msg user">${t}</div>`; 
            i.value = "";
            h.scrollTop = h.scrollHeight;

            const resRaw = await intentarLlamadaRobusta(`Actúa como Jefe de Servicio UCI. Respuesta breve y técnica basada en la guía: ${t}`);
            
            if(resRaw) {
                const resLimpia = limpiarMarkdown(resRaw);
                h.innerHTML += `<div class="msg ai">${marked.parse(resLimpia)}</div>`;
                h.scrollTop = h.scrollHeight;
            } else {
                h.innerHTML += `<div class="msg ai" style="color:red">Error de conexión.</div>`;
            }
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
