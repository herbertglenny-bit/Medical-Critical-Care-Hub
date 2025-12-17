import streamlit as st
import google.generativeai as genai
import PyPDF2

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Medical Critical Hub",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PROMPTS ---
PROMPT_ANALISIS = """
# ROL
Actúa como un Médico Intensivista Senior.
# OBJETIVO
Analizar la Guía de Práctica Clínica (GPC) adjunta.
# INSTRUCCIONES
1. Ficha Técnica (Título, Año, Sociedad, Población).
2. Análisis Delta: Nuevas recomendaciones fuertes, Conceptos obsoletos, Cambios en dosis.
3. Algoritmo Bedside: Resucitación, Mantenimiento, Destete.
4. Rincón del Residente: 3 Puntos clave, 3 Preguntas de examen, Evidencia clave.
5. Áreas de Incertidumbre.
"""

PROMPT_INFOGRAFIA = """
# ROL
Experto en Comunicación Visual y UCI.
# OBJETIVO
Estructurar Infografía One-Page.
# ESTRUCTURA
1. Encabezado.
2. Semáforo de Cambios (Rojo/Amarillo/Verde).
3. Algoritmo de Flujo.
4. The Big Numbers.
5. Resumen Ejecutivo.
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
        st.error(f"Error leyendo PDF: {e}")
        return None

# --- INTERFAZ ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063176.png", width=80)
    st.title("Medical Critical Hub")
    st.markdown("**Dr. Herbert Baquerizo Vargas**")
    st.caption("Althaia, Xarxa Assistencial Universitària de Manresa")
    st.divider()
    
    # Verificación de licencia
    if "GOOGLE_API_KEY" in st.secrets:
        st.success("✅ Licencia Activada")
    else:
        st.error("⚠️ Falta configurar el 'Secret' con la API Key.")
        
    st.divider()
    uploaded_file = st.file_uploader("Subir Guía (PDF)", type=['pdf'])

# --- LÓGICA PRINCIPAL ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    api_key = None

if uploaded_file and api_key:
    try:
        genai.configure(api_key=api_key)
        
        # CAMBIO CLAVE: Usamos 'gemini-pro' que es compatible con todo
        model = genai.GenerativeModel('gemini-pro') 

        if "pdf_text" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
            with st.spinner("Procesando documento..."):
                text = get_pdf_text(uploaded_file)
                st.session_state.pdf_text = text
                st.session_state.file_name = uploaded_file.name
                st.session_state.chat_history = []
        
        st.success(f"Guía cargada: {uploaded_file.name}")
        
        tab1, tab2, tab3 = st.tabs(["📋 Análisis", "🎨 Infografía", "💬 Chat"])

        with tab1:
            if st.button("Analizar Guía"):
                with st.spinner("Generando análisis..."):
                    # Usamos try-except para manejar errores de longitud
                    try:
                        prompt_completo = PROMPT_ANALISIS + "\n\nDOCUMENTO:\n" + st.session_state.pdf_text
                        response = model.generate_content(prompt_completo)
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Error al analizar: {e}")

        with tab2:
            if st.button("Crear Infografía"):
                with st.spinner("Diseñando visuales..."):
                    try:
                        prompt_completo = PROMPT_INFOGRAFIA + "\n\nDOCUMENTO:\n" + st.session_state.pdf_text
                        response = model.generate_content(prompt_completo)
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Error al diseñar: {e}")

        with tab3:
            for msg in st.session_state.chat_history:
                st.chat_message(msg["role"]).write(msg["content"])
            
            if prompt := st.chat_input("Pregunta a la guía..."):
                st.chat_message("user").write(prompt)
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                
                chat_prompt = f"Contexto: {st.session_state.pdf_text}\n\nPregunta: {prompt}\nResponde solo según el contexto."
                resp = model.generate_content(chat_prompt)
                
                st.chat_message("assistant").write(resp.text)
                st.session_state.chat_history.append({"role": "assistant", "content": resp.text})

    except Exception as e:
        st.error(f"Error general: {e}")
