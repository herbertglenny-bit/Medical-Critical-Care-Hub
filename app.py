import streamlit as st
import google.generativeai as genai
import PyPDF2
from streamlit_pdf_viewer import pdf_viewer
import base64

# Importamos la base de datos simulada
try:
    from database import library
except ImportError:
    library = []

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Medical Critical Care Hub",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS: ESTILOS PROFESIONALES ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
        }
        header {visibility: hidden;}
        /* Estilo para las tarjetas de la biblioteca */
        .guide-card {
            background-color: #f0f2f6;
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid #ff4b4b;
            margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# --- PROMPTS MAESTROS ---
PROMPT_ANALISIS = """
# ROL: Médico Intensivista Senior.
# OBJETIVO: Analizar GPC para sesión clínica.
# SALIDA: Markdown estructurado.
1. Ficha Técnica.
2. Análisis Delta (Novedades/Obsoleto).
3. Algoritmo Bedside.
4. Rincón del Residente (Learning Points/Preguntas).
5. Incertidumbre.
"""

PROMPT_INFOGRAFIA = """
# ROL: Experto Comunicación Visual.
# OBJETIVO: Infografía One-Page.
# SALIDA: Markdown estructurado.
1. Header.
2. Semáforo (Rojo/Amarillo/Verde).
3. Flujograma.
4. Big Numbers.
5. Take Home Messages.
"""

# --- FUNCIONES ---
def get_pdf_text(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except: return None

# --- INICIALIZACIÓN ESTADO ---
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "home" # home, detail, admin
if "selected_guide" not in st.session_state:
    st.session_state.selected_guide = None

# --- SIDEBAR DE NAVEGACIÓN ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063176.png", width=60)
    st.title("Medical Critical Care Hub")
    st.caption("Dr. Herbert Baquerizo Vargas")
    
    st.divider()
    
    # Menú Principal
    if st.button("🏠 Biblioteca de Guías", use_container_width=True):
        st.session_state.view_mode = "home"
        st.session_state.selected_guide = None
        st.rerun()

    st.divider()
    
    # Área Admin
    with st.expander("🔒 Área de Administrador"):
        admin_pass = st.text_input("Contraseña", type="password")
        if admin_pass == st.secrets.get("ADMIN_PASSWORD", "admin123"):
            if st.button("⚙️ Panel de Carga", use_container_width=True):
                st.session_state.view_mode = "admin"
                st.rerun()
        elif admin_pass:
            st.error("Contraseña incorrecta")

# ==========================================
# VISTA 1: HOME / BIBLIOTECA (PÚBLICA)
# ==========================================
if st.session_state.view_mode == "home":
    st.title("📚 Biblioteca de Guías Clínicas")
    
    # Filtros
    col_search, col_filter = st.columns([3, 1])
    with col_search:
        search_query = st.text_input("🔍 Buscar guía (Título, Sepsis, ARDS...)", "")
    with col_filter:
        especialidad_filter = st.selectbox("Especialidad", ["Todas", "Medicina Intensiva", "Cardiología", "Neumología", "Anestesia", "Infecciosas"])

    st.divider()
    
    # Grid de Resultados
    if not library:
        st.info("La biblioteca está vacía. Accede al panel Admin para publicar la primera guía.")
    
    for guide in library:
        # Lógica de filtrado simple
        match_search = search_query.lower() in guide['titulo'].lower() or search_query.lower() in guide['resumen'].lower()
        match_esp = especialidad_filter == "Todas" or especialidad_filter == guide['especialidad']
        
        if match_search and match_esp:
            with st.container():
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.subheader(f"{guide['titulo']}")
                    st.caption(f"📅 {guide['anio']} | 🏥 {guide['sociedad']} | 🩺 {guide['especialidad']}")
                    st.write(guide['resumen'])
                with c2:
                    st.write("")
                    st.write("")
                    if st.button("📖 Leer Guía", key=f"btn_{guide['id']}", use_container_width=True):
                        st.session_state.selected_guide = guide
                        st.session_state.view_mode = "detail"
                        st.rerun()
                st.divider()

# ==========================================
# VISTA 2: DETALLE DE GUÍA (SPLIT SCREEN)
# ==========================================
elif st.session_state.view_mode == "detail" and st.session_state.selected_guide:
    guide = st.session_state.selected_guide
    
    # Botón Volver
    if st.button("⬅️ Volver a la Biblioteca"):
        st.session_state.view_mode = "home"
        st.rerun()

    st.markdown(f"## {guide['titulo']}")
    
    # Configuración de Modelo para Chat (Si hay API Key)
    model = None
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-pro')

    # Layout
    col_izq, col_der = st.columns([1, 1])
    
    with col_izq:
        st.markdown("#### 📄 Documento Original")
        # NOTA: En la versión "Repositorio", el PDF debería descargarse de una URL o estar en local.
        # Como es una demo, avisamos si no hay PDF cargado en memoria.
        if "pdf_bytes" in guide:
             pdf_viewer(input=guide['pdf_bytes'], width=800, height=850)
        else:
            st.info("⚠️ Modo Lectura: El PDF original no está incrustado en esta demo. (El Admin debe subirlo a GitHub y enlazarlo).")
            st.markdown(f"**[🔗 Enlace a la fuente oficial]({guide.get('url_fuente', '#')})**")

    with col_der:
        st.markdown("#### 🤖 Análisis Inteligente")
        with st.container(height=850, border=True):
            tab1, tab2, tab3 = st.tabs(["📋 Análisis", "🎨 Infografía", "💬 Chat"])
            
            with tab1:
                st.markdown(guide['analisis'])
            
            with tab2:
                st.markdown(guide['infografia'])
            
            with tab3:
                # Chatbot específico para esta guía (usando el texto pre-analizado si existe)
                if "chat_history" not in st.session_state: st.session_state.chat_history = []
                
                for msg in st.session_state.chat_history:
                    st.chat_message(msg["role"]).write(msg["content"])
                
                if prompt := st.chat_input("Pregunta sobre esta guía..."):
                    st.chat_message("user").write(prompt)
                    st.session_state.chat_history.append({"role": "user", "content": prompt})
                    if model:
                        # RAG Simple usando el análisis como contexto (para ahorrar tokens/memoria)
                        ctx = guide['analisis'] + "\n" + guide['infografia']
                        resp = model.generate_content(f"Contexto médico:\n{ctx}\n\nPregunta: {prompt}")
                        st.chat_message("assistant").write(resp.text)
                        st.session_state.chat_history.append({"role": "assistant", "content": resp.text})
                    else:
                        st.error("Chat no disponible (Falta API Key)")

# ==========================================
# VISTA 3: ADMIN PANEL (CREADOR DE CONTENIDO)
# ==========================================
elif st.session_state.view_mode == "admin":
    st.title("⚙️ Panel de Publicación")
    st.info("Sube una guía, analízala y obtén el código para añadirla a `database.py`.")
    
    uploaded_file = st.file_uploader("Subir Nueva Guía (PDF)", type=['pdf'])
    
    c1, c2, c3 = st.columns(3)
    meta_titulo = c1.text_input("Título Guía")
    meta_sociedad = c2.text_input("Sociedad (ej. ESICM)")
    meta_esp = c3.selectbox("Especialidad", ["Medicina Intensiva", "Cardiología", "Neumología", "Anestesia", "Otros"])
    meta_anio = c1.text_input("Año")
    meta_resumen = st.text_area("Resumen Corto (para la tarjeta)")
    meta_url = st.text_input("URL Original (Link de descarga oficial)")

    if uploaded_file and "GOOGLE_API_KEY" in st.secrets:
        if st.button("🚀 ANALIZAR Y GENERAR CÓDIGO"):
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            
            # Intentar encontrar modelo Flash o Pro
            try:
                available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                target = next((m for m in available if 'flash' in m), 'models/gemini-pro')
                model = genai.GenerativeModel(target)
                
                with st.spinner("Leyendo PDF..."):
                    pdf_text = get_pdf_text(uploaded_file)
                
                with st.spinner("Generando Análisis Clínico..."):
                    res_analisis = model.generate_content(PROMPT_ANALISIS + "\nDOC:\n" + pdf_text).text
                    
                with st.spinner("Generando Infografía..."):
                    res_info = model.generate_content(PROMPT_INFOGRAFIA + "\nDOC:\n" + pdf_text).text
                
                st.success("¡Análisis Completado!")
                st.divider()
                
                # GENERADOR DE CÓDIGO
                # Esto crea el bloque de texto exacto que debes pegar en database.py
                code_snippet = f"""
    {{
        "id": "{meta_titulo.replace(' ', '_').lower()}",
        "titulo": "{meta_titulo}",
        "sociedad": "{meta_sociedad}",
        "especialidad": "{meta_esp}",
        "anio": "{meta_anio}",
        "resumen": "{meta_resumen}",
        "url_fuente": "{meta_url}",
        "analisis": \"\"\"{res_analisis}\"\"\",
        "infografia": \"\"\"{res_info}\"\"\",
        "pdf_bytes": None  # Nota: Para ver el PDF real, se requiere configuración avanzada de almacenamiento.
    }},
                """
                st.subheader("📋 Código para Publicar")
                st.markdown("Copia el siguiente bloque y pégalo dentro de la lista `library` en tu archivo `database.py` en GitHub:")
                st.code(code_snippet, language="python")
                
            except Exception as e:
                st.error(f"Error: {e}")
