import streamlit as st
import google.generativeai as genai
import PyPDF2
from streamlit_pdf_viewer import pdf_viewer
import base64
from PIL import Image

# Importamos la base de datos (si falla, iniciamos vacío)
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

# --- ESTILOS CSS (Visualización limpia) ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 2rem; }
        .guide-card {
            background-color: #f0f2f6;
            padding: 15px;
            border-radius: 10px;
            border-left: 5px solid #ff4b4b;
            margin-bottom: 10px;
        }
        /* Ajuste para que el chat no ocupe demasiado espacio vertical */
        .stChatInput { position: fixed; bottom: 0; }
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN API KEY ---
# Intentamos leer de los secrets de Streamlit Cloud
api_key = st.secrets.get("GOOGLE_API_KEY")

if not api_key:
    st.error("⚠️ No se detectó la API Key en los Secrets. El análisis IA no funcionará.")
else:
    genai.configure(api_key=api_key)

# --- FUNCIONES AUXILIARES ---
def get_pdf_text(pdf_file):
    """Extrae texto del PDF para enviarlo a la IA"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except: return ""

def get_model():
    """Selecciona el mejor modelo disponible (Flash es rápido y acepta muchas imágenes)"""
    return genai.GenerativeModel('gemini-1.5-flash')

# --- VARIABLES DE SESIÓN ---
if "view_mode" not in st.session_state: st.session_state.view_mode = "home"
if "selected_guide" not in st.session_state: st.session_state.selected_guide = None

# ==========================================
# BARRA LATERAL (Navegación)
# ==========================================
with st.sidebar:
    st.title("🏥 Critical Care Hub")
    st.caption("Dr. Herbert Baquerizo Vargas")
    st.divider()
    
    if st.button("🏠 Biblioteca", use_container_width=True):
        st.session_state.view_mode = "home"
        st.rerun()

    st.divider()
    
    # Acceso Admin
    with st.expander("🔒 Admin"):
        password = st.text_input("Clave", type="password")
        if password == st.secrets.get("ADMIN_PASSWORD", "admin123"):
            if st.button("Ir al Panel de Carga"):
                st.session_state.view_mode = "admin"
                st.rerun()

# ==========================================
# VISTA 1: HOME (Biblioteca)
# ==========================================
if st.session_state.view_mode == "home":
    st.header("📚 Guías Clínicas Disponibles")
    
    # Filtros simples
    filtro = st.text_input("🔍 Buscar por título o patología...", "")
    
    for guide in library:
        # Lógica de búsqueda
        texto_busqueda = (guide['titulo'] + guide['resumen'] + guide['especialidad']).lower()
        if filtro.lower() in texto_busqueda:
            with st.container():
                st.markdown(f"""
                <div class="guide-card">
                    <h3>{guide['titulo']}</h3>
                    <p><b>{guide['sociedad']} ({guide['anio']})</b> | 🩺 {guide['especialidad']}</p>
                    <p>{guide['resumen']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"📖 Abrir Guía", key=guide['id']):
                    st.session_state.selected_guide = guide
                    st.session_state.view_mode = "detail"
                    st.rerun()

# ==========================================
# VISTA 2: DETALLE (Lectura + IA)
# ==========================================
elif st.session_state.view_mode == "detail" and st.session_state.selected_guide:
    guide = st.session_state.selected_guide
    
    # Botón volver
    if st.button("⬅️ Volver atrás"):
        st.session_state.view_mode = "home"
        st.rerun()

    st.subheader(f"{guide['titulo']}")
    
    # --- LAYOUT DIVIDIDO ---
    col_pdf, col_ia = st.columns([1, 1])
    
    # COLUMNA IZQUIERDA: VISOR PDF
    with col_pdf:
        st.info("💡 Haz scroll aquí para leer el documento original.")
        if guide.get('pdf_bytes'):
            pdf_viewer(input=guide['pdf_bytes'], width=700, height=800)
        else:
            st.warning("PDF no almacenado internamente. Ver enlace fuente.")
            st.markdown(f"[🔗 Ver documento original]({guide['url_fuente']})")

    # COLUMNA DERECHA: ANÁLISIS + CHAT
    with col_ia:
        tab1, tab2, tab3 = st.tabs(["📋 Análisis", "📊 Infografía", "💬 Chatbot & Gráficos"])
        
        # PESTAÑA 1: ANÁLISIS
        with tab1:
            st.markdown(guide['analisis'])
            
        # PESTAÑA 2: INFOGRAFÍA
        with tab2:
            st.markdown(guide['infografia'])
            
        # PESTAÑA 3: CHATBOT INTERACTIVO
        with tab3:
            st.write("Pregunta sobre la guía o sube un recorte de una tabla/gráfico.")
            
            # Historial del chat
            if "chat_history" not in st.session_state: st.session_state.chat_history = []
            
            # Mostrar mensajes anteriores
            for msg in st.session_state.chat_history:
                role_icon = "👨‍⚕️" if msg["role"] == "user" else "🤖"
                st.chat_message(msg["role"], avatar=role_icon).write(msg["content"])
                if "image" in msg:
                    st.chat_message(msg["role"], avatar=role_icon).image(msg["image"], width=200)

            # Uploader para imágenes (Tablas/Gráficos) dentro del chat
            img_file = st.file_uploader("📷 Adjuntar tabla/gráfico (Opcional)", type=["png", "jpg", "jpeg"], key="chat_img")
            
            # Input de texto
            pregunta = st.chat_input("Escribe tu duda clínica aquí...")
            
            if pregunta:
                # 1. Mostrar pregunta usuario
                st.chat_message("user", avatar="👨‍⚕️").write(pregunta)
                user_msg = {"role": "user", "content": pregunta}
                
                img_data = None
                if img_file:
                    image = Image.open(img_file)
                    st.chat_message("user", avatar="👨‍⚕️").image(image, width=200)
                    user_msg["image"] = image
                    img_data = image
                
                st.session_state.chat_history.append(user_msg)
                
                # 2. Generar respuesta IA
                with st.spinner("Consultando guía..."):
                    try:
                        model = get_model()
                        
                        # Construimos el contexto con el análisis ya hecho para ahorrar tokens
                        contexto = f"""
                        ERES UN ASISTENTE MÉDICO EXPERTO.
                        Contexto de la guía clínica:
                        {guide['analisis']}
                        {guide['infografia']}
                        
                        PREGUNTA DEL USUARIO: {pregunta}
                        """
                        
                        inputs = [contexto]
                        if img_data:
                            inputs.append(img_data)
                            inputs.append("Analiza esta imagen (tabla o gráfico) en el contexto médico de la pregunta.")
                        
                        response = model.generate_content(inputs)
                        
                        st.chat_message("assistant", avatar="🤖").write(response.text)
                        st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                        
                    except Exception as e:
                        st.error(f"Error de conexión: {e}")

# ==========================================
# VISTA 3: ADMIN (Generador de Código)
# ==========================================
elif st.session_state.view_mode == "admin":
    st.title("⚙️ Panel de Carga de Guías")
    st.info("Sube el PDF, rellena los datos y la IA generará el código para `database.py`.")
    
    # 1. Subir Archivo
    uploaded_file = st.file_uploader("1. Sube el PDF", type=['pdf'])
    
    # 2. Datos Manuales (Más seguro que automáticos)
    c1, c2 = st.columns(2)
    titulo = c1.text_input("Título")
    sociedad = c2.text_input("Sociedad/Autores")
    c3, c4 = st.columns(2)
    anio = c3.text_input("Año")
    especialidad = c4.selectbox("Especialidad", ["Medicina Intensiva", "Cardiología", "Infecciosas", "Otra"])
    resumen = st.text_area("Resumen breve")
    
    if uploaded_file and st.button("🚀 ANALIZAR Y GENERAR CÓDIGO"):
        if not api_key:
            st.error("Falta API Key")
        else:
            with st.spinner("Leyendo PDF y Analizando con Gemini... esto puede tardar unos segundos..."):
                try:
                    # A. Leer PDF completo
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    full_text = ""
                    for page in pdf_reader.pages:
                        full_text += page.extract_text() or ""
                    
                    # B. Convertir PDF a Base64 para guardarlo
                    uploaded_file.seek(0)
                    pdf_b64 = base64.b64encode(uploaded_file.read()).decode('utf-8')
                    
                    # C. Prompt de Análisis
                    prompt_analisis = f"""
                    Actúa como Médico Intensivista. Analiza este texto de una guía clínica:
                    {full_text[:30000]} 
                    
                    Genera un resumen estructurado en Markdown con:
                    1. Título oficial y autores.
                    2. Puntos clave (Bullet points).
                    3. Resumen de recomendaciones principales.
                    """
                    
                    # D. Prompt Infografía
                    prompt_info = f"""
                    Basado en el texto anterior, crea una infografía en texto Markdown:
                    - Usa emojis de semáforo (🟢 🔴 🟡).
                    - Lista de "Hacer" vs "No hacer".
                    - Algoritmo simplificado en texto.
                    """
                    
                    model = get_model()
                    res_analisis = model.generate_content(prompt_analisis).text
                    res_info = model.generate_content(prompt_info).text
                    
                    # E. Generar el Bloque de Código
                    safe_id = titulo.replace(" ", "_").lower()[:15]
                    
                    code_block = f"""
    {{
        "id": "{safe_id}",
        "titulo": "{titulo}",
        "sociedad": "{sociedad}",
        "especialidad": "{especialidad}",
        "anio": "{anio}",
        "resumen": "{resumen}",
        "url_fuente": "#",
        "analisis": \"\"\"{res_analisis}\"\"\",
        "infografia": \"\"\"{res_info}\"\"\",
        "pdf_bytes": base64.b64decode("{pdf_b64}")
    }},
                    """
                    
                    st.success("¡Análisis completado! Copia el siguiente código y pégalo en `database.py`:")
                    st.code(code_block, language="python")
                    st.warning("⚠️ Nota: Recuerda importar 'base64' al inicio de database.py si no está.")
                    
                except Exception as e:
                    st.error(f"Error procesando: {e}")
