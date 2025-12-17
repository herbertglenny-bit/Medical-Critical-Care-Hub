import os
import time
import google.generativeai as genai
from pypdf import PdfReader
import streamlit as st

# ==========================================
# 1. TU CLAVE AQUÍ
# ==========================================
GEMINI_API_KEY = "AQUI_TU_CLAVE_AIzaSy..." 

CARPETA_PDFS = "." 

# ==========================================
# 2. CONEXIÓN INTELIGENTE (AUTO-SELECTOR + RETRY)
# ==========================================
ESTADO_CEREBRO = "Iniciando..."
model = None

try:
    if "AIza" not in GEMINI_API_KEY:
        ESTADO_CEREBRO = "❌ ERROR: FALTA CLAVE"
    else:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # --- RECUPERAMOS EL AUTO-SELECTOR QUE SÍ FUNCIONABA ---
        modelo_elegido = ""
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    if 'gemini' in m.name:
                        modelo_elegido = m.name
                        break
        except:
            pass
        
        if not modelo_elegido: modelo_elegido = 'gemini-pro'

        print(f"✅ Modelo recuperado: {modelo_elegido}")
        model = genai.GenerativeModel(modelo_elegido)
        ESTADO_CEREBRO = "✅ CONECTADO"

except Exception as e:
    ESTADO_CEREBRO = f"❌ ERROR TÉCNICO: {str(e)}"

# ==========================================
# 3. PROMPT DE INTENSIVISTA (EL BUENO)
# ==========================================

def analizar_con_ia(texto, archivo):
    if "ERROR" in ESTADO_CEREBRO:
        return None, None
    
    prompt = f"""
    Actúa como un Médico Intensivista Senior. Analiza este PDF: "{archivo}".
    Genera una respuesta con DOS PARTES separadas por "---SEPARADOR---".

    PARTE 1: EL ANÁLISIS (Markdown)
    - # Ficha Técnica (Título, Año, Sociedad)
    - # Puntos Clave (3-4 bullets con lo más importante)
    - # Resumen Ejecutivo (De qué trata en 2 líneas)
    - # Algoritmo Bedside (Describe los pasos de decisión clínica en lista numerada)

    PARTE 2: LA INFOGRAFÍA (Muy breve)
    - # Semáforo (🟢 Hacer / 🔴 Evitar)
    
    ---SEPARADOR---
    (Aquí empieza parte 2)

    TEXTO PDF: {texto[:25000]} 
    """
    
    try:
        # Pausa de 4 segundos para evitar el error 429 (Cuota)
        time.sleep(4) 
        response = model.generate_content(prompt)
        texto_completo = response.text
        
        if "---SEPARADOR---" in texto_completo:
            partes = texto_completo.split("---SEPARADOR---")
            return partes[0].strip(), partes[1].strip()
        else:
            return texto_completo, "Error visual."
    except Exception as e:
        return f"Error IA: {e}", "Error visual"

# ==========================================
# 4. MOTOR CON MEMORIA (PARA NO GASTAR SALDO)
# ==========================================

@st.cache_data(show_spinner=False) 
def generar_biblioteca_automatica():
    biblioteca = []
    
    if not os.path.exists(CARPETA_PDFS):
        return []

    archivos = sorted([f for f in os.listdir(CARPETA_PDFS) if f.lower().endswith('.pdf')])

    for archivo in archivos:
        try:
            ruta = os.path.join(CARPETA_PDFS, archivo)
            with open(ruta, "rb") as f:
                contenido_bytes = f.read()
            
            reader = PdfReader(ruta)
            texto_pdf = ""
            for page in reader.pages[:10]: 
                texto_pdf += page.extract_text() or ""
        except:
            contenido_bytes = None
            texto_pdf = ""

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

library = generar_biblioteca_automatica()
