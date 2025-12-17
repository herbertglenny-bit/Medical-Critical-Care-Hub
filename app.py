import streamlit as st
import google.generativeai as genai
import PyPDF2
from streamlit_pdf_viewer import pdf_viewer
import base64
import json

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

# --- CSS: ESTILOS ---
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
        .guide-card {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 5px solid #ff4b4b;
            margin-bottom: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

# --- PROMPTS MAESTROS ---
PROMPT_METADATA = """
Actúa como bibliotecario médico. Analiza la primera página de este documento y extrae la siguiente información en formato JSON estricto:
{
    "titulo": "Título completo de la guía",
    "sociedad": "Nombre de la sociedad médica o autores (ej. ESICM, AHA)",
    "anio": "Año de publicación",
    "especialidad": "La especialidad médica más probable (ej. Medicina Intensiva, Cardiología)",
    "resumen": "Un resumen de 2 líneas sobre el objetivo de la guía EN CASTELLANO."
}
Si no encuentras algún dato, déjalo en blanco.
"""

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
def get_pdf_text(pdf_file, pages=None):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        limit = len(pdf_reader.pages) if pages is None else min(pages, len(pdf_reader.pages))
        for i in range(limit):
            text += pdf_reader.pages[i].extract_text() or ""
        return text
    except: return None

# --- INICIALIZACIÓN ESTADO ---
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "home"
if "selected_guide" not in st.session_state:
    st.session_state.selected_guide = None
if "admin_form" not in st.session_state:
    st.session_state.admin_form = {}

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3063/3063176.png", width=60)
    st.title("Medical Critical Care Hub")
    st.caption("Dr. Herbert Baquerizo Vargas")
    st.divider()
    
    if st.button("🏠 Biblioteca de Guías", use_container_width=True):
        st.session_state.view_mode = "home"
        st.session_state.selected_guide = None
        st.rerun()

    st.divider()
    
    with st.expander("🔒 Área de Administrador"):
        admin_pass = st.text_input("Contraseña", type="password")
        correct_pass = st.secrets.get("ADMIN_PASSWORD", "admin123")
        if admin_pass == correct_pass:
            if st.button("⚙️ Panel de Carga", use_container_width=True):
                st.session_state.view_mode = "admin"
                st.rerun()
        elif admin_pass:
            st.error("Acceso denegado")

# --- LÓGICA API KEY ---
api_key = st.secrets.get("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# ==========================================
# VISTA 1: HOME (BIBLIOTECA)
# ==========================================
if st.session_state.view_mode == "home":
    st.title("📚 Biblioteca de Guías Clínicas")
    
    col_search, col_filter = st.columns([3, 1])
    with col_search:
        search_query = st.text_input("🔍 Buscar guía...", "")
    with col_filter:
        especialidad_filter = st.selectbox("Especialidad", ["Todas", "Medicina Intensiva", "Cardiología", "Neumología", "Anestesia", "Infecciosas"])

    st.divider()
    
    if not library:
        st.info("La biblioteca está vacía. Accede al panel Admin para publicar la primera guía.")
    
    for guide in library:
        match_search = search_query.lower() in guide['titulo'].lower() or search_query.lower() in guide['resumen'].lower()
        match_esp = especialidad_filter == "Todas" or especialidad_filter == guide['especialidad']
        
        if match_search and match_esp:
            with st.container():
                st.markdown(f"""
                <div class="guide-card">
                    <h3>{guide['titulo']}</h3>
                    <p style="color:gray;">📅 {guide['anio']} | 🏥 {guide['sociedad']} | 🩺 {guide['especialidad']}</p>
                    <p>{guide['resumen']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("📖 Leer Guía Completa", key=f"btn_{guide['id']}"):
                    st.session_state.selected_guide = guide
                    st.session_state.view_mode = "detail"
                    st.rerun()

# ==========================================
# VISTA 2: DETALLE
# ==========================================
elif st.session_state.view_mode == "detail" and st.session_state.selected_guide:
    guide = st.session_state.selected_guide
    
    if st.button("⬅️ Volver a la Biblioteca"):
        st.session_state.view_mode = "home"
        st.rerun()

    st.markdown(f"## {guide['titulo']}")
    
    col_izq, col_der = st.columns([1, 1])
    
    with col_izq:
        c1, c2, c3 = st.columns([2, 3, 2])
        with c1: st.markdown("#### 📄 Original")
        with c2: zoom_level = st.slider("🔍 Zoom", 600, 2000, 800, label_visibility="collapsed")
        with c3: st.write("")
        
        with st.container(height=850, border=True):
            if "pdf_bytes" in guide and guide["pdf_bytes"]:
                 pdf_viewer(input=guide['pdf_bytes'], width=zoom_level)
            else:
                st.info("PDF no disponible en esta demo.")
                st.markdown(f"**[🔗 Link externo]({guide.get('url_fuente', '#')})**")

    with col_der:
        st.markdown("#### 🤖 Análisis Inteligente")
        with st.container(height=850, border=True):
            tab1, tab2, tab3 = st.tabs(["📋 Análisis", "🎨 Infografía", "💬 Chat"])
            
            with tab1: st.markdown(guide['analisis'])
            with tab2: st.markdown(guide['infografia'])
            with tab3:
                if "chat_history" not in st.session_state: st.session_state.chat_history = []
                for msg in st.session_state.chat_history:
                    st.chat_message(msg["role"]).write(msg["content"])
                
                if prompt := st.chat_input("Pregunta sobre esta guía..."):
                    st.chat_message("user").write(prompt)
                    st.session_state.chat_history.append({"role": "user", "content": prompt})
                    if api_key:
                        model = genai.GenerativeModel('gemini-pro')
                        ctx = guide['analisis'] + "\n" + guide['infografia']
                        try:
                            resp = model.generate_content(f"Contexto médico:\n{ctx}\n\nPregunta: {prompt}")
                            st.chat_message("assistant").write(resp.text)
                            st.session_state.chat_history.append({"role": "assistant", "content": resp.text})
                        except Exception as e:
                            st.error(f"Error: {e}")

# ==========================================
# VISTA 3: ADMIN
# ==========================================
elif st.session_state.view_mode == "admin":
    st.title("⚙️ Panel de Publicación Inteligente")
    
    uploaded_file = st.file_uploader("1. Sube la Guía (PDF)", type=['pdf'])
    
    if uploaded_file and api_key:
        if "last_uploaded" not in st.session_state or st.session_state.last_uploaded != uploaded_file.name:
            with st.spinner("🤖 Extrayendo metadatos..."):
                try:
                    text_preview = get_pdf_text(uploaded_file, pages=3)
                    model = genai.GenerativeModel('gemini-pro')
                    # Aseguramos cierre de paréntesis aquí
                    response = model.generate_content(PROMPT_METADATA + f"\n\nTEXTO:\n{text_preview}")
                    
                    json_str = response.text.replace("```json", "").replace("```", "").strip()
                    metadata = json.loads(json_str)
                    st.session_state.admin_form = metadata
                    st.session_state.last_uploaded = uploaded_file.name
                    st.toast("¡Datos extraídos!", icon="✨")
                except Exception as e:
                    st.error(f"Error metadatos: {e}")

    st.subheader("2. Revisa y Completa")
    defaults = st.session_state.get("admin_form", {})
    
    c1, c2, c3 = st.columns(3)
    meta_titulo = c1.text_input("Título Guía", value=defaults.get("titulo", ""))
    meta_sociedad = c2.text_input("Sociedad", value=defaults.get("sociedad", ""))
    meta_anio = c3.text_input("Año", value=defaults.get("anio", ""))
    
    c4, c5 = st.columns([1, 2])
    meta_esp = c4.text_input("Especialidad", value=defaults.get("especialidad", ""))
    meta_url = c5.text_input("URL Original (Opcional)")
    
    meta_resumen = st.text_area("Resumen (Castellano)", value=defaults.get("resumen", ""), height=100)

    st.divider()

    if uploaded_file and st.button("3. 🚀 GENERAR CÓDIGO"):
        with st.spinner("Analizando documento completo..."):
            try:
                # Buscamos modelo disponible
                available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                target_model = next((m for m in available if 'flash' in m), 'models/gemini-pro')
                model_flash = genai.GenerativeModel(target_model)
                
                full_text = get_pdf_text(uploaded_file)
                
                # Generamos contenido con paréntesis seguros
                res_analisis = model_flash.generate_content(PROMPT_ANALISIS + "\nDOC:\n" + full_text).text
                res_info = model_flash.generate_content(PROMPT_INFOGRAFIA + "\nDOC:\n" + full_text).text
                
                safe_id = meta_titulo.replace(' ', '_').lower()[:20]
                
                code_snippet = f"""
    {{
        "id": "{safe_id}",
        "titulo": "{meta_titulo}",
        "sociedad": "{meta_sociedad}",
        "especialidad": "{meta_esp}",
        "anio": "{meta_anio}",
        "resumen": "{meta_resumen}",
        "url_fuente": "{meta_url}",
        "analisis": \"\"\"{res_analisis}\"\"\",
        "infografia": \"\"\"{res_info}\"\"\",
        "pdf_bytes": None 
    }},
                """
                st.success("¡Listo! Copia este bloque en database.py:")
                st.code(code_snippet, language="python")
                
            except Exception as e:
                st.error(f"Error en generación: {e}")
