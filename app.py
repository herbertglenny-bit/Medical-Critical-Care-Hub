import streamlit as st
import google.generativeai as genai
import PyPDF2

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Medical Critical Hub",
    page_icon="🏥",
    layout="wide"
)

# --- INTERFAZ ---
with st.sidebar:
    st.title("Medical Critical Hub")
    st.caption("Dr. Herbert Baquerizo Vargas | Althaia")
    st.divider()
    
    # Verificación de licencia
    if "GOOGLE_API_KEY" in st.secrets:
        st.success("✅ API Key Detectada")
    else:
        st.error("⚠️ Falta API Key en Secrets")
        
    uploaded_file = st.file_uploader("Subir Guía (PDF)", type=['pdf'])

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

# --- LÓGICA DE DIAGNÓSTICO Y EJECUCIÓN ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    api_key = None

if uploaded_file and api_key:
    genai.configure(api_key=api_key)
    
    # --- AUTO-BUSCADOR DE MODELOS (La solución al error 404) ---
    st.info("🔄 Conectando con Google para buscar modelos disponibles...")
    
    target_model = None
    try:
        # Pedimos a la API que nos diga qué modelos ve esta Llave
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # Intentamos encontrar uno compatible
        st.write(f"Modelos encontrados para tu llave: `{available_models}`")
        
        if 'models/gemini-1.5-flash' in available_models:
            target_model = 'models/gemini-1.5-flash'
        elif 'models/gemini-pro' in available_models:
            target_model = 'models/gemini-pro'
        elif len(available_models) > 0:
            target_model = available_models[0] # Cogemos el primero que haya
            
    except Exception as e:
        st.error(f"❌ Error grave de conexión con Google: {e}")
        st.warning("Posible causa: Tu API Key no tiene permisos o está restringida en tu región.")

    # SI ENCONTRAMOS MODELO, EJECUTAMOS
    if target_model:
        st.success(f"✅ Conectado exitosamente usando el modelo: **{target_model}**")
        model = genai.GenerativeModel(target_model)
        
        # Procesar PDF
        if "pdf_text" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
            text = get_pdf_text(uploaded_file)
            st.session_state.pdf_text = text
            st.session_state.file_name = uploaded_file.name
        
        # Botón de análisis simple para probar
        if st.button("ANALIZAR DOCUMENTO AHORA"):
            with st.spinner("Analizando..."):
                try:
                    response = model.generate_content(f"Resume este texto médico en 3 puntos clave:\n\n{st.session_state.pdf_text[:5000]}")
                    st.markdown("### Resultado:")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Error generando: {e}")
    
    elif not target_model and 'available_models' in locals():
        st.error("❌ Tu API Key funciona, pero Google dice que NO tienes acceso a ningún modelo Gemini.")
        st.markdown("""
        **Solución:**
        1. Ve a [Google AI Studio](https://aistudio.google.com/).
        2. Crea una **NUEVA** API Key.
        3. Asegúrate de que tienes un proyecto seleccionado.
        4. Actualiza el "Secret" en Streamlit.
        """)

elif not api_key:
    st.warning("Configura tu API Key en los Secrets.")
