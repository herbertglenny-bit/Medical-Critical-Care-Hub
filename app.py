import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import base64
import json
import re
from datetime import datetime
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="NanoBanana UCI Station", layout="wide")

# --- 2. MOTOR IA ---
def configurar_ia():
    try:
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("⚠️ Configura GEMINI_API_KEY en Secrets.")
            return None, None
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        seleccion = next((m for m in modelos if "flash" in m), modelos[0] if modelos else None)
        return (genai.GenerativeModel(seleccion), seleccion) if seleccion else (None, None)
    except:
        return None, None

model_ia, nombre_modelo = configurar_ia()

# --- 3. BASE DE DATOS ---
def get_db_connection():
    return sqlite3.connect('guias_medicas.db', check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS guias 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, fecha TEXT, 
                         pdf_blob BLOB, analisis_md TEXT, infografia_html TEXT)''')
init_db()

# --- 4. INTERFAZ LATERAL ---
with st.sidebar:
    st.title("🍌 NanoBanana UCI")
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    
    with get_db_connection() as conn:
        guias = conn.execute('SELECT id, titulo FROM guias ORDER BY id DESC').fetchall()
    
    for g_id, g_titulo in guias:
        col_t, col_b = st.columns([0.8, 0.2])
        with col_t:
            if st.button(f"📄 {g_titulo}", key=f"g_{g_id}", use_container_width=True):
                st.session_state['active_guide_id'] = g_id
                st.rerun()
        with col_b:
            if modo_admin:
                if st.button("🗑️", key=f"del_{g_id}"):
                    with get_db_connection() as conn:
                        conn.execute('DELETE FROM guias WHERE id = ?', (g_id,))
                    st.rerun()

# --- 5. MODO ADMINISTRADOR (CARGA) ---
if modo_admin:
    st.header("Carga y Gestión de Guías")
    file = st.file_uploader("Subir GPC (PDF)", type="pdf")
    
    if file and st.button("🚀 PROCESAR E INSERTAR"):
        with st.spinner("Analizando contenido técnico..."):
            try:
                pdf_data = file.read()
                doc_input = {'mime_type': 'application/pdf', 'data': pdf_data}
                
                # Prompt 1: Análisis técnico (sin mensajes de "Jefe")
                p1 = "Analiza este PDF clínico en ESPAÑOL. Proporciona un resumen técnico estructurado: 1. Metodología, 2. Cambios respecto a versiones previas, 3. Algoritmos de tratamiento, 4. Puntos clave de seguridad. No añadas introducciones ni despedidas."
                analisis = model_ia.generate_content([p1, doc_input]).text
                
                # Prompt 2: Infografía
                p2 = "Genera un DIV HTML profesional para un póster médico. Colores: Blanco, Negro, Amarillo (#ffd600). Secciones: Acciones inmediatas, Métricas y Semáforo de riesgo."
                infografia = model_ia.generate_content([p2, doc_input]).text
                
                with get_db_connection() as conn:
                    conn.execute('INSERT INTO guias (titulo, fecha, pdf_blob, analisis_md, infografia_html) VALUES (?,?,?,?,?)',
                                 (file.name, datetime.now().strftime("%Y-%m-%d"), pdf_data, analisis, infografia))
                st.success("✅ Guía procesada con éxito.")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# --- 6. DASHBOARD USUARIO (VISUALIZACIÓN) ---
elif 'active_guide_id' in st.session_state:
    with get_db_connection() as conn:
        guia = conn.execute('SELECT * FROM guias WHERE id = ?', (st.session_state['active_guide_id'],)).fetchone()
    
    if guia:
        st.title(f"📍 {guia[1]}")
        col_visor, col_info = st.columns([1, 1])
        
        with col_visor:
            st.subheader("Documento Original")
            pdf_b64 = base64.b64encode(guia[3]).decode('utf-8')
            # Visor embebido corregido
            pdf_display = f'<iframe src="data:application/pdf;base64,{pdf_b64}" width="100%" height="1000px" style="border:none;"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
            
        with col_info:
            tabs = st.tabs(["📝 Análisis Técnico", "📊 Póster Visual", "🤖 Chat Experto"])
            
            with tabs[0]:
                st.markdown(f'<div style="background-color:white; color:black; padding:20px; border-radius:10px; border:1px solid #ddd;">{guia[4]}</div>', unsafe_allow_html=True)
            
            with tabs[1]:
                components.html(f'<div style="background:white; min-height:100vh;">{guia[5]}</div>', height=1000, scrolling=True)
            
            with tabs[2]:
                st.subheader("Consulta a la Guía")
                pregunta = st.text_input("Haz una pregunta técnica sobre este PDF:")
                if pregunta:
                    with st.spinner("Consultando..."):
                        doc_input = {'mime_type': 'application/pdf', 'data': guia[3]}
                        resp = model_ia.generate_content([f"Responde de forma técnica y breve en español: {pregunta}", doc_input])
                        st.chat_message("assistant").write(resp.text)

else:
    st.title("Estación de Trabajo NanoBanana UCI")
    st.info("👈 Selecciona una guía clínica en el lateral.")
