import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Medical Critical Hub",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PROMPTS MAESTROS (DEFINIDOS POR EL USUARIO) ---

PROMPT_ANALISIS = """
# ROL
Actúa como un Médico Intensivista Senior y Experto en Educación Médica Universitaria. Tu tarea es analizar en profundidad la Guía de Práctica Clínica (GPC) proporcionada.

# OBJETIVO
El objetivo es diseccionar este documento para una sesión clínica del Servicio de Medicina Intensiva. La audiencia incluye adjuntos y residentes.

# INSTRUCCIONES DE ANÁLISIS
Genera un informe estructurado que cubra los siguientes puntos clave. Utiliza un tono profesional, técnico y preciso. Usa Markdown para formatear títulos y listas.

## 1. Ficha Técnica Resumida
* **Título de la Guía y Sociedad(es) Emisora(s):**
* **Año de publicación:**
* **Población diana:**
* **Metodología:**

## 2. Análisis Delta: ¿Qué hay de nuevo?
Compara esta guía con su versión previa o práctica estándar.
* **Nuevas Recomendaciones Fuertes:** (Clase I o Fuertes que no existían o cambiaron).
* **Conceptos Obsoletos:** (Prácticas desaconsejadas explícitamente).
* **Cambios en Dosis/Umbrales:**

## 3. Algoritmo de Manejo Práctico (Bedside)
Protocolo paso a paso para el manejo diario.
* **Fase de Resucitación/Aguda:**
* **Fase de Mantenimiento:**
* **Fase de Destete/Salida:**
* Incluye Bundles si los hay.

## 4. Rincón del Residente (Docencia)
* **3 "Key Learning Points":** Conceptos fisiopatológicos/terapéuticos clave.
* **Preguntas de Guardia:** 3 preguntas tipo test o caso corto con respuesta razonada.
* **Evidencia Clave:** Ensayos clínicos (RCT) fundamentales mencionados.

## 5. Áreas de Incertidumbre
* Lagunas en la evidencia o recomendaciones débiles.

NOTA: Si hay tablas de dosis o escalas, formatéalas como tablas Markdown.
"""

PROMPT_INFOGRAFIA = """
# ROL
Actúa como un Experto en Comunicación Científica Visual y Médico Intensivista.

# OBJETIVO
Estructurar la información de la Guía para crear una Infografía Técnica de Alto Impacto. Texto telegráfico, directo y jerarquizado. NO incluyas casos clínicos.

# ESTRUCTURA DE SALIDA
## SECCIÓN 1: Encabezado
* Título Corto e Impactante.
* Subtítulo.
* Etiquetas de Contexto.

## SECCIÓN 2: El Semáforo de Cambios
Crea una tabla con:
* ROJO (STOP): Prácticas a abandonar.
* AMARILLO (PRECAUCIÓN): Áreas de incertidumbre.
* VERDE (GO): Intervenciones recomendadas.
* Sugiere iconos entre corchetes.

## SECCIÓN 3: Algoritmo de Flujo
Diagrama de flujo lógico con flechas (-->).
* Inicio.
* Pasos (1, 2, 3...).

## SECCIÓN 4: "The Big Numbers"
Cifras clave (dosis, tiempos, umbrales) para poner en grande.

## SECCIÓN 5: Resumen Ejecutivo
* 3 Mensajes para llevar a casa (Take Home Messages).
* Nivel de Evidencia global.
"""

# --- FUNCIONES AUXILIARES ---

def get_pdf_text(pdf_file):
    """Extrae texto de un archivo PDF."""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        st.error(f"Error al leer el PDF: {e}")
        return None

def stream_gemini_response(model, prompt, content):
    """Envía solicitud a Gemini y devuelve el stream."""
    try:
        full_prompt = f"{prompt}\n\n--- CONTENIDO DEL DOCUMENTO ---\n{content}"
        response = model.generate_content(full_prompt, stream=True)
        return response
    except Exception as e:
        st.error(f"Error en la API de Gemini: {e}")
        return None

# --- INTERFAZ SIDEBAR ---

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063176.png", width=80) # Icono genérico médico
    st.title("Medical Critical Hub")
    st.markdown("**Dr. Herbert Baquerizo Vargas**")
    st.caption("Althaia, Xarxa Assistencial Universitària de Manresa")
    
    st.divider()
    
    api_key = st.text_input("Ingresa tu Google API Key", type="password", help="Obtén tu clave en aistudio.google.com")
    
    st.divider()
    
    uploaded_file = st.file_uploader("Subir Guía (PDF)", type=['pdf'])
    
    st.info("⚠️ **Aviso:** Esta herramienta utiliza IA. Verifica siempre las respuestas con el documento original.")

# --- LÓGICA PRINCIPAL ---

if uploaded_file is not None and api_key:
    # Configurar Gemini
    genai.configure(api_key=api_key)
    # Usamos Gemini 1.5 Flash por ser rápido y tener gran ventana de contexto
    model = genai.GenerativeModel('gemini-1.5-flash') 

    # Extraer texto (Solo una vez)
    if "pdf_text" not in st.session_state or st.session_state.uploaded_filename != uploaded_file.name:
        with st.spinner("Leyendo documento..."):
            text = get_pdf_text(uploaded_file)
            if text:
                st.session_state.pdf_text = text
                st.session_state.uploaded_filename = uploaded_file.name
                # Limpiar historial de chat al cambiar de archivo
                st.session_state.chat_history = [] 
            else:
                st.stop()

    st.success(f"Archivo cargado: **{uploaded_file.name}**")

    # Pestañas
    tab1, tab2, tab3 = st.tabs(["📋 Análisis Clínico", "🎨 Infografía", "💬 Chat con la Guía"])

    # TAB 1: ANÁLISIS
    with tab1:
        st.header("Análisis de Medicina Intensiva")
        if st.button("Generar Análisis Clínico", key="btn_analisis"):
            with st.spinner("Analizando guía con criterio de experto..."):
                response_stream = stream_gemini_response(model, PROMPT_ANALISIS, st.session_state.pdf_text)
                if response_stream:
                    st.write_stream(response_stream)

    # TAB 2: INFOGRAFÍA
    with tab2:
        st.header("Estructura para Infografía")
        if st.button("Generar Datos Visuales", key="btn_info"):
            with st.spinner("Estructurando información visual..."):
                response_stream = stream_gemini_response(model, PROMPT_INFOGRAFIA, st.session_state.pdf_text)
                if response_stream:
                    st.write_stream(response_stream)

    # TAB 3: CHATBOT (RAG SIMPLE)
    with tab3:
        st.header("Interrogar al Documento")
        
        # Inicializar historial si no existe
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # Mostrar historial
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Input del usuario
        if prompt := st.chat_input("Ej: ¿Cuál es la dosis de carga recomendada?"):
            # Guardar y mostrar pregunta usuario
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generar respuesta
            with st.chat_message("assistant"):
                try:
                    # Construir prompt de chat con contexto
                    chat_prompt = f"""
                    Actúa como un asistente médico experto. Responde a la pregunta basándote ÚNICAMENTE en el siguiente contexto extraído de una guía clínica.
                    Si la respuesta no está en el texto, di "No encuentro esa información en este documento".
                    
                    PREGUNTA: {prompt}
                    
                    CONTEXTO DEL DOCUMENTO:
                    {st.session_state.pdf_text}
                    """
                    
                    response_stream = model.generate_content(chat_prompt, stream=True)
                    response_text = st.write_stream(response_stream)
                    
                    # Guardar respuesta en historial
                    st.session_state.chat_history.append({"role": "assistant", "content": response_text})
                    
                except Exception as e:
                    st.error(f"Error: {e}")

elif uploaded_file and not api_key:
    st.warning("👈 Por favor, introduce tu Google API Key en la barra lateral para comenzar.")
    
else:
    st.markdown("""
    ### 👋 Bienvenido al Medical Critical Hub
    **Plataforma de Análisis Inteligente de Guías Clínicas**
    
    Esta herramienta te permite:
    1. **Subir** un PDF de una guía (ej. SSC Sepsis, ARDS ESICM).
    2. **Obtener** un análisis estructurado para sesión clínica.
    3. **Diseñar** el contenido para una infografía "One-Pager".
    4. **Chatear** con la guía para resolver dudas puntuales.
    
    *Creado por Dr. Herbert Baquerizo Vargas.*
    """)
