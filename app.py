import streamlit as st
import google.generativeai as genai
import PyPDF2
import base64

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Medical Critical Care Hub",
    page_icon="🏥",
    layout="wide", # IMPRESCINDIBLE para pantalla dividida
    initial_sidebar_state="expanded"
)

# --- PROMPTS MAESTROS ---
PROMPT_ANALISIS = """
# ROL
Actúa como un Médico Intensivista Senior y Experto en Educación Médica Universitaria.
# OBJETIVO
Analizar en profundidad la Guía de Práctica Clínica (GPC) adjunta para una sesión clínica.
# INSTRUCCIONES DE ANÁLISIS
Genera un informe estructurado que cubra los siguientes puntos clave.
## 1. Ficha Técnica Resumida
* Título, Sociedad, Año, Población, Metodología.
## 2. Análisis Delta: ¿Qué hay de nuevo?
* Nuevas Recomendaciones Fuertes.
* Conceptos Obsoletos (Lo que debemos dejar de hacer).
* Cambios en Dosis/Umbrales.
## 3. Algoritmo de Manejo Práctico (Bedside)
* Fase de Resucitación/Aguda.
* Fase de Mantenimiento.
* Fase de Destete/Salida.
## 4. Rincón del Residente (Docencia)
* 3 "Key Learning Points".
* 3 Preguntas de Guardia (tipo test/caso corto con respuesta).
* Evidencia Clave (Ensayos clínicos mencionados).
## 5. Áreas de Incertidumbre
"""

PROMPT_INFOGRAFIA = """
# ROL
Actúa como un Experto en Comunicación Científica Visual y Médico Intensivista.
# OBJETIVO
Estructurar la información de la Guía para crear una Infografía Técnica de Alto Impacto (One-Page Visual Summary).
# ESTRUCTURA DE SALIDA
## SECCIÓN 1: Encabezado
* Título Corto, Subtítulo y Etiquetas.
## SECCIÓN 2: El Semáforo de Cambios
* ROJO (STOP): Prácticas a abandonar.
* AMARILLO (PRECAUCIÓN): Áreas de incertidumbre.
* VERDE (GO): Intervenciones recomendadas.
## SECCIÓN 3: Algoritmo de Flujo
* Diagrama de flujo lógico paso a paso.
## SECCIÓN 4: "The Big Numbers"
* Cifras clave (dosis, tiempos, umbrales) para poner en grande.
## SECCIÓN 5: Resumen Ejecutivo
* 3 Mensajes para llevar a casa.
* Nivel de Evidencia global.
"""

# --- FUNCIONES ---
def get_pdf_text(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return None

def display_pdf(uploaded_file):
    """Muestra el PDF en un iframe"""
    bytes_data = uploaded_file.getvalue()
    base64_pdf = base64.b64encode(bytes_data).decode('utf-8')
    # Altura ajustada a 900px para que ocupe bien la pantalla
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="900px" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# --- INTERFAZ ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063176.png", width=80)
    st.title("Medical Critical Care Hub")
    st.markdown("**Dr. Herbert Baquerizo Vargas**")
    st.caption("Althaia, Xarxa Assistencial Universitària de Manresa")
    st.divider()
    
    if "GOOGLE_API_KEY" in st.secrets:
        st.success("✅ Licencia Activada")
    else:
        st.error("⚠️ Falta API Key en Secrets")
        
    st.divider()
    uploaded_file = st.file_uploader("Subir Guía (PDF)", type=['pdf'])

# --- LÓGICA PRINCIPAL ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    api_key = None

if uploaded_file and api_key:
    genai.configure(api_key=api_key)
    
    # --- AUTO-SELECCIÓN DE MODELO ---
    if "target_model" not in st.session_state:
        try:
            available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if any('flash' in m for m in available):
                st.session_state.target_model = next(m for m in available if 'flash' in m)
            elif any('pro' in m for m in available):
                st.session_state.target_model = next(m for m in available if 'pro' in m)
            elif available:
                st.session_state.target_model = available[0]
            else:
                st.error("No se encontraron modelos disponibles.")
        except:
            st.session_state.target_model = 'models/gemini-pro'

    # Configuramos el modelo
    model = genai.GenerativeModel(st.session_state.target_model)
    
    # Procesar PDF (Texto)
    if "pdf_text" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
        with st.spinner(f"Procesando documento con {st.session_state.target_model}..."):
            text = get_pdf_text(uploaded_file)
            st.session_state.pdf_text = text
            st.session_state.file_name = uploaded_file.name
            st.session_state.chat_history = []
    
    # --- LAYOUT DE PANTALLA DIVIDIDA ---
    # Creamos dos columnas iguales
    col_izq, col_der = st.columns(2)
    
    # --- COLUMNA IZQUIERDA: EL PDF ---
    with col_izq:
        st.subheader("📄 Documento Original")
        # Botón de descarga
        st.download_button(
            label="💾 Descargar PDF",
            data=uploaded_file.getvalue(),
            file_name=uploaded_file.name,
            mime="application/pdf"
        )
        st.divider()
        # Visor
        display_pdf(uploaded_file)
        
    # --- COLUMNA DERECHA: LA IA ---
    with col_der:
        st.subheader("🤖 Análisis Inteligente")
        
        # Las 3 Pestañas de herramientas
        tab1, tab2, tab3 = st.tabs(["📋 Análisis", "🎨 Infografía", "💬 Chat"])

        # TAB 1: ANÁLISIS
        with tab1:
            st.info("Genera un resumen clínico estructurado.")
            if st.button("Generar Informe Intensivista", key="btn_analisis"):
                with st.spinner("Analizando evidencia..."):
                    try:
                        full_prompt = PROMPT_ANALISIS + "\n\nDOCUMENTO:\n" + st.session_state.pdf_text
                        response = model.generate_content(full_prompt)
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Error: {e}")

        # TAB 2: INFOGRAFÍA
        with tab2:
            st.info("Extrae los datos clave para diseño visual.")
            if st.button("Generar Estructura Visual", key="btn_info"):
                with st.spinner("Estructurando datos..."):
                    try:
                        full_prompt = PROMPT_INFOGRAFIA + "\n\nDOCUMENTO:\n" + st.session_state.pdf_text
                        response = model.generate_content(full_prompt)
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Error: {e}")

        # TAB 3: CHATBOT
        with tab3:
            st.info("Pregunta dudas específicas al documento.")
            # Contenedor para el historial (para que no se mezcle con el input)
            chat_container = st.container()
            with chat_container:
                for msg in st.session_state.chat_history:
                    st.chat_message(msg["role"]).write(msg["content"])
            
            # Input de chat
            if prompt := st.chat_input("Pregunta a la guía..."):
                st.chat_message("user").write(prompt)
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                
                try:
                    chat_prompt = f"Actúa como experto médico. Contexto de la guía:\n{st.session_state.pdf_text}\n\nPregunta: {prompt}\nRespuesta:"
                    resp = model.generate_content(chat_prompt)
                    st.chat_message("assistant").write(resp.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": resp.text})
                except Exception as e:
                    st.error(f"Error respondiendo: {e}")

elif not api_key:
    st.warning("⚠️ Configura la API Key en los Secrets.")
