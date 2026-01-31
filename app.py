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

# --- 2. MOTOR IA Y SEGURIDAD ---
def init_gemini():
    try:
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("⚠️ Configura GEMINI_API_KEY en los Secrets de Streamlit.")
            st.stop()
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return True
    except Exception as e:
        st.error(f"Error de configuración: {e}")
        return False

def get_best_model():
    # Lista estática de respaldo para evitar latencia en consultas de modelos
    return "gemini-1.5-flash"

if init_gemini():
    ACTIVE_MODEL = get_best_model()

# --- 3. BASE DE DATOS (ESTABLE) ---
def get_db_connection():
    conn = sqlite3.connect('guias_medicas.db', check_same_thread=False)
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS guias 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         titulo TEXT, fecha TEXT, pdf_blob BLOB, 
                         analisis_md TEXT, infografia_html TEXT, mermaid_code TEXT)''')

def guardar_guia(titulo, pdf_bytes, analisis, html, mermaid):
    with get_db_connection() as conn:
        conn.execute('''INSERT INTO guias (titulo, fecha, pdf_blob, analisis_md, infografia_html, mermaid_code) 
                        VALUES (?, ?, ?, ?, ?, ?)''', 
                     (titulo, datetime.now().strftime("%Y-%m-%d"), pdf_bytes, analisis, html, mermaid))

def obtener_guias():
    with get_db_connection() as conn:
        return conn.execute('SELECT id, titulo, fecha FROM guias ORDER BY id DESC').fetchall()

def obtener_guia_por_id(g_id):
    with get_db_connection() as conn:
        return conn.execute('SELECT * FROM guias WHERE id = ?', (g_id,)).fetchone()

init_db()

# --- 4. FUNCIONES DE LIMPIEZA ---
def clean_ai_output(text, type="md"):
    text = text.replace("```markdown", "").replace("```html", "").replace("```mermaid", "").replace("```", "")
    if type == "html":
        match = re.search(r'<div', text)
        if match: text = text[match.start():]
    return text.strip()

# --- 5. LOGICA DE NAVEGACIÓN ---
with st.sidebar:
    st.title("🍌 NanoBanana UCI")
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    
    guias_list = obtener_guias()
    for g_id, g_titulo, g_fecha in guias_list:
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            if st.button(f"📄 {g_titulo}", key=f"btn_{g_id}", use_container_width=True):
                st.session_state['active_guide_id'] = g_id
        with col2:
            if modo_admin:
                if st.button("🗑️", key=f"del_{g_id}"):
                    with get_db_connection() as conn:
                        conn.execute('DELETE FROM guias WHERE id = ?', (g_id,))
                    st.rerun()

# --- 6. FLUJO DE TRABAJO ---
if modo_admin:
    st.header("Admin: Procesar Nueva Guía")
    file = st.file_uploader("Subir GPC (PDF)", type="pdf")
    
    if file and st.button("🚀 PROCESAR GUÍA"):
        with st.spinner("La IA está analizando la evidencia científica..."):
            pdf_bytes = file.read()
            model = genai.GenerativeModel(ACTIVE_MODEL)
            
            # Análisis Médico
            p1 = "Actúa como Jefe de UCI. Idioma: Español. Analiza el PDF y genera un resumen estructurado con: Metodología, Novedades (Análisis Delta), Bundles de tratamiento y Mini-caso clínico para residentes."
            res_analisis = clean_ai_output(model.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p1]).text)
            
            # Visual Poster
            p2 = "Genera un fragmento de HTML (SOLO el DIV) con clases de Material Design para un póster médico. Incluye secciones para Semáforo (Stop/Wait/Go) y métricas clave."
            res_html = clean_ai_output(model.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p2]).text, "html")
            
            # Algoritmo Mermaid
            p3 = "Genera un diagrama de flujo Mermaid TD sobre el protocolo de esta guía. Solo el código, sin bloques de markdown."
            res_mermaid = clean_ai_output(model.generate_content([{'mime_type': 'application/pdf', 'data': pdf_bytes}, p3]).text)
            
            guardar_guia(file.name, pdf_bytes, res_analisis, res_html, res_mermaid)
            st.success("✅ Guía procesada y guardada exitosamente.")
            st.rerun()

# --- 7. DASHBOARD OPERATIVO ---
if 'active_guide_id' in st.session_state:
    guia = obtener_guia_por_id(st.session_state['active_guide_id'])
    if guia:
        # Preparación de datos para el Template
        pdf_b64 = base64.b64encode(guia[3]).decode('utf-8')
        
        # Inyección de datos en el Template (Usando el template que proporcionaste con correcciones)
        # Nota: Aquí se usa el html_template original, asegúrate de que las variables coincidan.
        from string import Template
        
        # Simplificación de la lógica de reemplazo para evitar errores de JSON
        # (Aquí va tu html_template del código original con los placeholders __PDF_DATA__, etc.)
        # Por brevedad, asumo el uso de componentes.html con el template procesado.
        
        # REEMPLAZO SEGURO
        final_html = html_template.replace("__API_KEY__", st.secrets.get("GEMINI_API_KEY", ""))
        final_html = final_html.replace("__MODELS_JSON__", json.dumps([ACTIVE_MODEL]))
        final_html = final_html.replace("__PDF_DATA__", json.dumps(pdf_b64))
        final_html = final_html.replace("__ANALISIS_DATA__", json.dumps(guia[4]))
        final_html = final_html.replace("__INFO_DATA__", json.dumps(guia[5]))
        final_html = final_html.replace("__MERMAID_DATA__", json.dumps(guia[6]))
        
        components.html(final_html, height=1000, scrolling=True)
else:
    st.title("Estación de Trabajo UCI NanoBanana")
    st.markdown("""
    ### Bienvenido al Handover Médico Digital
    Selecciona una guía clínica del panel izquierdo para comenzar el análisis.
    
    **Capacidades:**
    * 📑 Lectura de PDF integrada.
    * 🤖 Chat experto sobre la guía.
    * 📊 Infografías generadas por IA.
    * 🗺️ Diagramas de flujo automáticos.
    """)
