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

# --- 2. MOTOR IA CON AUTODETECCIÓN DE CAPACIDADES ---
def configurar_ia():
    try:
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("⚠️ Falta GEMINI_API_KEY en Secrets.")
            return None, None
        
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        
        # Interrogamos a la API para ver qué modelos tienes disponibles
        modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Priorizamos modelos 'flash' por su velocidad y soporte de PDF
        seleccion = next((m for m in modelos_disponibles if "flash" in m), modelos_disponibles[0] if modelos_disponibles else None)
        
        if seleccion:
            return genai.GenerativeModel(seleccion), seleccion
        return None, None
    except Exception as e:
        st.error(f"Error al conectar con el servidor de Google: {e}")
        return None, None

model_ia, nombre_modelo = configurar_ia()

# --- 3. BASE DE DATOS (REFORZADA) ---
def get_db_connection():
    return sqlite3.connect('guias_medicas.db', check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS guias 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         titulo TEXT, fecha TEXT, pdf_blob BLOB, 
                         analisis_md TEXT, infografia_html TEXT, mermaid_code TEXT)''')
init_db()

# --- 4. INTERFAZ LATERAL ---
with st.sidebar:
    st.title("🍌 NanoBanana UCI")
    if nombre_modelo:
        st.caption(f"Motor activo: {nombre_modelo}")
    
    modo_admin = st.checkbox("⚙️ Modo Administrador")
    st.divider()
    
    with get_db_connection() as conn:
        guias = conn.execute('SELECT id, titulo FROM guias ORDER BY id DESC').fetchall()
    
    for g_id, g_titulo in guias:
        if st.button(f"📄 {g_titulo}", key=f"g_{g_id}", use_container_width=True):
            st.session_state['active_guide_id'] = g_id
            st.rerun()

# --- 5. LÓGICA DE PROCESAMIENTO (ADMIN) ---
if modo_admin:
    st.header("Panel de Carga de Evidencia")
    
    # Botón de backup para seguridad del médico
    with get_db_connection() as conn:
        datos_backup = conn.execute('SELECT * FROM guias').fetchall()
        if datos_backup:
            st.download_button("📥 Descargar Copia de Seguridad (JSON)", 
                             json.dumps(datos_backup, default=str), 
                             f"backup_uci_{datetime.now().strftime('%Y%m%d')}.json")

    file = st.file_uploader("Subir GPC en PDF", type="pdf")
    
    if file and st.button("🚀 ANALIZAR Y PUBLICAR"):
        if not model_ia:
            st.error("No hay conexión con la IA. Revisa tu API Key.")
        else:
            with st.spinner("Procesando... La IA está leyendo el PDF."):
                try:
                    pdf_data = file.read()
                    doc_input = {'mime_type': 'application/pdf', 'data': pdf_data}
                    
                    # Ejecución de prompts médicos
                    p1 = "Eres Jefe de UCI. Resume este PDF en ESPAÑOL: 1. Metodología, 2. Cambios clave (Delta), 3. Bundles de tratamiento, 4. Perlas para residentes."
                    analisis = model_ia.generate_content([p1, doc_input]).text
                    
                    p2 = "Genera un DIV HTML para un póster médico. Usa colores: Negro, Blanco y Amarillo (#ffd600). Incluye secciones: Semáforo y Métricas clave. Usa emojis."
                    infografia = model_ia.generate_content([p2, doc_input]).text
                    
                    # Limpieza rápida de etiquetas markdown
                    analisis = analisis.replace("```markdown", "").replace("```", "").strip()
                    infografia = infografia.replace("```html", "").replace("```", "").strip()
                    
                    with get_db_connection() as conn:
                        conn.execute('''INSERT INTO guias (titulo, fecha, pdf_blob, analisis_md, infografia_html) 
                                        VALUES (?, ?, ?, ?, ?)''', 
                                     (file.name, datetime.now().strftime("%Y-%m-%d"), pdf_data, analisis, infografia))
                    
                    st.success("✅ Guía procesada y guardada en la base de datos.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error técnico: {e}")

# --- 6. DASHBOARD OPERATIVO (USUARIO) ---
elif 'active_guide_id' in st.session_state:
    with get_db_connection() as conn:
        guia = conn.execute('SELECT * FROM guias WHERE id = ?', (st.session_state['active_guide_id'],)).fetchone()
    
    if guia:
        st.title(f"📍 {guia[1]}")
        col_pdf, col_dashboard = st.columns([1, 1])
        
        with col_pdf:
            st.subheader("Visor de Guía")
            pdf_base64 = base64.b64encode(guia[3]).decode('utf-8')
            pdf_embed = f'<iframe src="data:application/pdf;base64,{pdf_base64}" width="100%" height="900" type="application/pdf"></iframe>'
            st.markdown(pdf_embed, unsafe_allow_html=True)
            
        with col_dashboard:
            pestanas = st.tabs(["📝 Resumen Ejecutivo", "📊 Póster UCI"])
            with pestanas[0]:
                st.markdown(guia[4])
            with pestanas[1]:
                # Inyectamos el HTML de la infografía de forma segura
                components.html(f"""
                    <div style="font-family: sans-serif;">
                        {guia[5]}
                    </div>
                """, height=900, scrolling=True)
else:
    st.title("Estación de Trabajo NanoBanana UCI")
    st.info("👈 Selecciona una guía clínica en el menú lateral para visualizar el análisis.")
