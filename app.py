import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import base64
import json
import re
import io
from datetime import datetime
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="NanoBanana UCI Station", layout="wide")

# --- 2. MOTOR IA (Configuración segura desde Secrets) ---
def init_gemini():
    try:
        if "GEMINI_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            return True
        else:
            st.error("⚠️ Falta la clave API en Secrets.")
            return False
    except:
        return False

init_gemini()
ACTIVE_MODEL = "gemini-1.5-flash"

# --- 3. BASE DE DATOS (Funciones esenciales) ---
def get_db_connection():
    return sqlite3.connect('guias_medicas.db', check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS guias 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         titulo TEXT, fecha TEXT, pdf_blob BLOB, 
                         analisis_md TEXT, infografia_html TEXT, mermaid_code TEXT)''')

def obtener_guias():
    with get_db_connection() as conn:
        return conn.execute('SELECT id, titulo, fecha FROM guias ORDER BY id DESC').fetchall()

def obtener_guia_por_id(g_id):
    with get_db_connection() as conn:
        return conn.execute('SELECT * FROM guias WHERE id = ?', (g_id,)).fetchone()

init_db()

# --- 4. FUNCIONES DE EMERGENCIA (Backup) ---
def exportar_datos():
    with get_db_connection() as conn:
        # Convertimos la base de datos a un archivo descargable
        data = conn.execute('SELECT * FROM guias').fetchall()
        return json.dumps(data, default=str)

def importar_datos(json_str):
    data = json.loads(json_str)
    with get_db_connection() as conn:
        conn.execute('DELETE FROM guias') # Limpiamos para evitar duplicados
        for row in data:
            conn.execute('''INSERT INTO guias (titulo, fecha, pdf_blob, analisis_md, infografia_html, mermaid_code) 
                            VALUES (?, ?, ?, ?, ?, ?)''', (row[1], row[2], row[3], row[4], row[5], row[6]))
        conn.commit()

# --- 5. INTERFAZ LATERAL ---
with st.sidebar:
    st.title("🍌 NanoBanana UCI")
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    
    guias_list = obtener_guias()
    for g_id, g_titulo, g_fecha in guias_list:
        if st.button(f"📄 {g_titulo}", key=f"btn_{g_id}", use_container_width=True):
            st.session_state['active_guide_id'] = g_id

# --- 6. CUERPO PRINCIPAL ---
if modo_admin:
    st.header("⚙️ Panel de Control")
    
    # SECCIÓN DE BACKUP
    with st.expander("💾 Gestión de Datos (Copia de Seguridad)"):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Descargar mis guías actuales"):
                backup = exportar_datos()
                st.download_button("Click para guardar archivo", backup, file_name="backup_guias.json")
        with col2:
            archivo_importar = st.file_uploader("Subir copia de seguridad", type="json")
            if archivo_importar and st.button("📤 Restaurar datos"):
                importar_datos(archivo_importar.read().decode())
                st.success("¡Datos restaurados!")
                st.rerun()

    st.divider()
    
    # PROCESAMIENTO DE GUÍAS
    file = st.file_uploader("Subir nueva Guía (PDF)", type="pdf")
    if file and st.button("🚀 ANALIZAR GUÍA"):
        with st.spinner("Analizando..."):
            # (Aquí iría tu lógica de generación de contenido con genai...)
            st.info("Guía procesada correctamente (Simulación)") 
            # Nota: Asegúrate de pegar aquí los prompts que ya tenías.

elif 'active_guide_id' in st.session_state:
    st.success(f"Visualizando Guía ID: {st.session_state['active_guide_id']}")
    # Aquí va el código de visualización que ya tienes
else:
    st.title("Estación de Trabajo UCI")
    st.info("Selecciona una guía en el menú de la izquierda.")
