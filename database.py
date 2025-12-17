import os
import time
import google.generativeai as genai
from pypdf import PdfReader
import streamlit as st

# ==========================================
# 1. TU CLAVE AQUÍ (IMPORTANTE: NO BORRES LAS COMILLAS)
# ==========================================
GEMINI_API_KEY = "AIzaSyBy9wai4pEyFCGQUiALSCzqYMOSj2foTjM" 

CARPETA_PDFS = "." 

# ==========================================
# 2. CONEXIÓN (MODELO ESTÁNDAR 1.5)
# ==========================================
ESTADO_CEREBRO = "Iniciando..."
model = None

try:
    # Verificamos que la clave no sea el texto de ejemplo
    if "AQUI_TU_CLAVE" in GEMINI_API_KEY:
        ESTADO_CEREBRO = "❌ ERROR: NO HAS PUESTO LA CLAVE"
    else:
        genai.configure(api_key=GEMINI_API_KEY)
        # Usamos el modelo 1.5 Flash (Gratuito y rápido)
        model = genai.GenerativeModel('gemini-1.5-flash')
        ESTADO_CEREBRO = "✅ CONECTADO"
except Exception as e:
    ESTADO_CEREBRO = f"❌ ERROR TÉCNICO: {str(e)}"

# ==========================================
# 3. FUNCIONES DE ANÁLISIS
# ==========================================

def analizar_con_ia(texto, archivo):
    if "ERROR" in ESTADO_CEREBRO:
        return None, None
    
    prompt = f"""
    Actúa como un Médico Intensivista Senior.
    Analiza este PDF: "{archivo}".

    Genera una respuesta con DOS PARTES separadas por "---SEPARADOR---".

    PARTE 1: EL ANÁLISIS (Markdown)
    - # Ficha Técnica (1 línea)
    - # Puntos Clave (3 bullets)
    - # Resumen Ejecutivo (Breve)
    - # Algoritmo (Si aplica, descríbelo en texto paso a paso)

    PARTE 2: LA INFOGRAFÍA (Muy breve)
    - # Semáforo (🟢 Hacer / 🔴 Evitar)
    
    ---SEPARADOR---
    (Aquí empieza parte 2)

    TEXTO: {texto[:25000]} 
    """
    
    try:
        # Pausa de seguridad para evitar Error 429
        time.sleep(2) 
        response = model.generate_content(prompt)
        texto_completo = response.text
        
        if "---SEPARADOR---" in texto_completo:
            partes = texto_completo.split("---SEPARADOR---")
            return partes[0].strip(), partes[1].strip()
        else:
            return texto_completo, "Error de formato visual."
    except Exception as e:
        return f"Error IA: {e}", "Error visual"

# ==========================================
# 4. MOTOR CON MEMORIA (CACHÉ)
# ==========================================

@st.cache_data(show_spinner=False) 
def generar_biblioteca_automatica():
    biblioteca = []
    
    if not os.path.exists(CARPETA_PDFS):
        return []

    archivos = sorted([f for f in os.listdir(CARPETA_PDFS) if f.lower().endswith('.pdf')])

    for archivo in archivos:
        # Leer PDF físico
        try:
            ruta = os.path.join(CARPETA_PDFS, archivo)
            with open(ruta, "rb") as f:
                contenido_bytes = f.read()
            
            reader = PdfReader(ruta)
            texto_pdf = ""
            # Leemos primeras 10 páginas
            for page in reader.pages[:10]: 
                texto_pdf += page.extract_text() or ""
        except:
            contenido_bytes = None
            texto_pdf = ""

        # GENERAR CONTENIDO
        if "CONECTADO" in ESTADO_CEREBRO:
            if len(texto_pdf) > 50:
                analisis_texto, infografia_texto = analizar_con_ia(texto_pdf, archivo)
                resumen_texto = "Análisis IA completado."
            else:
                analisis_texto = "PDF sin texto leíble."
                infografia_texto = "Error"
                resumen_texto = "PDF vacío."
        else:
            analisis_texto = f"# Error\n{ESTADO_CEREBRO}"
            infografia_texto = "❌ Offline"
            resumen_texto = "Error de conexión."

        item = {
            "id": archivo,
            "titulo": archivo.replace(".pdf", "").replace("_", " ").title(),
            "sociedad": "Auto",
            "especialidad": "UCI",
            "anio": "2024",
            "resumen": resumen_texto,
            "url_fuente": "",
            "pdf_source": None,
            "pdf_bytes": contenido_bytes,
            "analisis": analisis_texto,
            "infografia": infografia_texto
        }
        biblioteca.append(item)

    return biblioteca

# Ejecutamos
library = generar_biblioteca_automatica()
