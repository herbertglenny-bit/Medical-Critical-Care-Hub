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
def init_gemini():
    try:
        if "GEMINI_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            return True
        st.error("⚠️ Configura la GEMINI_API_KEY en Secrets.")
        return False
    except:
        return False

init_gemini()
ACTIVE_MODEL = "gemini-1.5-flash"

# --- 3. BASE DE DATOS ---
def get_db_connection():
    return sqlite3.connect('guias_medicas.db', check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS guias 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         titulo TEXT, fecha TEXT, pdf_blob BLOB, 
                         analisis_md TEXT, infografia_html TEXT, mermaid_code TEXT)''')
init_db()

# --- 4. FUNCIONES DE LIMPIEZA ---
def clean_ai_output(text, mode="md"):
    text = text.replace("```markdown", "").replace("```html", "").replace("```mermaid", "").replace("```", "")
    if mode == "html":
        match = re.search(r'<div', text)
        if match: text = text[match.start():]
    return text.strip()

# --- 5. INTERFAZ LATERAL ---
with st.sidebar:
    st.title("🍌 NanoBanana UCI")
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    
    with get_db_connection() as conn:
        guias_list = conn.execute('SELECT id, titulo, fecha FROM guias ORDER BY id DESC').fetchall()
    
    for g_id, g_titulo, g_fecha in guias_list:
        if st.button(f"📄 {g_titulo}", key=f"btn_{g_id}", use_container_width=True):
            st.session_state['active_guide_id'] = g_id
            st.rerun()

# --- 6. MODO ADMINISTRADOR (Carga y Procesamiento) ---
if modo_admin:
    st.header("⚙️ Panel de Control: Procesar GPC")
    
    # Copia de seguridad
    with st.expander("💾 Copia de Seguridad (Evitar borrados)"):
        if st.button("📥 Descargar Backup"):
            with get_db_connection() as conn:
                data = conn.execute('SELECT * FROM guias').fetchall()
                st.download_button("Guardar archivo JSON", json.dumps(data, default=str), "backup.json")
    
    file = st.file_uploader("Subir Guía PDF", type="pdf")
    
    if file and st.button("🚀 INICIAR PROCESAMIENTO REAL"):
        with st.spinner("La IA está leyendo y diseñando el póster..."):
            pdf_bytes = file.read()
            model = genai.GenerativeModel(ACTIVE_MODEL)
            
            # 1. Análisis Médico
            p1 = "Rol: Jefe de UCI. Idioma: Español. Analiza: Metodología, Novedades, Bundles y un Mini-caso para residentes."
            res_analisis = clean_ai_output(model.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p1]).text)
            
            # 2. Póster HTML
            p2 = "Genera un póster médico en HTML usando clases: poster-header, poster-body, traffic-container (tc-stop, tc-wait, tc-go), metrics-grid."
            res_html = clean_ai_output(model.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p2]).text, "html")
            
            # 3. Mermaid
            p3 = "Genera código Mermaid TD del protocolo. Solo código."
            res_mermaid = clean_ai_output(model.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p3]).text)
            
            # GUARDAR EN BD
            with get_db_connection() as conn:
                conn.execute('''INSERT INTO guias (titulo, fecha, pdf_blob, analisis_md, infografia_html, mermaid_code) 
                                VALUES (?, ?, ?, ?, ?, ?)''', 
                             (file.name, datetime.now().strftime("%Y-%m-%d"), pdf_bytes, res_analisis, res_html, res_mermaid))
            st.success("✅ Guía guardada. Desactiva el Modo Admin para verla.")

# --- 7. MODO USUARIO (Visualización y Chat) ---
elif 'active_guide_id' in st.session_state:
    with get_db_connection() as conn:
        guia = conn.execute('SELECT * FROM guias WHERE id = ?', (st.session_state['active_guide_id'],)).fetchone()
    
    if guia:
        pdf_b64 = base64.b64encode(guia[3]).decode('utf-8')
        
        # Aquí inyectamos tu HTML_TEMPLATE original (el que tiene los tabs y el chat)
        # Asegúrate de que el html_template esté definido arriba o pégalo aquí
        # Por espacio, usaré una versión simplificada del reemplazo:
        
        # NOTA: Usa aquí la variable `html_template` que tenías originalmente
        # Reemplazando los datos:
        render_ready = html_template.replace("__API_KEY__", st.secrets["GEMINI_API_KEY"])
        render_ready = render_ready.replace("__PDF_DATA__", json.dumps(pdf_b64))
        render_ready = render_ready.replace("__ANALISIS_DATA__", json.dumps(guia[4]))
        render_ready = render_ready.replace("__INFO_DATA__", json.dumps(guia[5]))
        render_ready = render_ready.replace("__MERMAID_DATA__", json.dumps(guia[6]))
        render_ready = render_ready.replace("__MODELS_JSON__", json.dumps([ACTIVE_MODEL]))

        components.html(render_ready, height=1200, scrolling=False)

else:
    st.title("Estación UCI NanoBanana")
    st.info("👈 Selecciona una guía en el menú lateral para empezar.")
