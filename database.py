import os
import google.generativeai as genai
from pypdf import PdfReader

# ==========================================
# 1. TU CLAVE AQUÍ
# ==========================================
GEMINI_API_KEY = "AIzaSyBy9wai4pEyFCGQUiALSCzqYMOSj2foTjM"

CARPETA_PDFS = "." 

# ==========================================
# 2. CONEXIÓN INTELIGENTE (AUTO-SELECTOR)
# ==========================================
ESTADO_CEREBRO = "Iniciando..."
model = None

try:
    if "AIza" not in GEMINI_API_KEY:
        ESTADO_CEREBRO = "❌ ERROR DE CLAVE"
    else:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # --- LA MAGIA: BUSCAMOS UN MODELO QUE FUNCIONE ---
        modelo_elegido = None
        try:
            # Preguntamos a Google qué modelos tiene
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    if 'gemini' in m.name:
                        modelo_elegido = m.name
                        break # Encontramos uno, nos quedamos con este
        except:
            pass

        # Si no encontramos ninguno en la lista, probamos el más nuevo por defecto
        if not modelo_elegido:
            modelo_elegido = 'gemini-1.5-flash'
            
        print(f"Modelo seleccionado: {modelo_elegido}")
        model = genai.GenerativeModel(modelo_elegido)
        ESTADO_CEREBRO = "✅ CONECTADO"

except Exception as e:
    ESTADO_CEREBRO = f"❌ ERROR: {str(e)}"

# ==========================================
# 3. MOTOR DE ANÁLISIS
# ==========================================

def analizar_con_ia(texto, archivo):
    if "ERROR" in ESTADO_CEREBRO:
        return None 
    
    prompt = f"""
    Eres un médico intensivista. Resume este PDF ({archivo}) en Markdown.
    
    Estructura:
    1. **Título del Documento**
    2. **Resumen Ejecutivo** (2 líneas)
    3. **3 Puntos Clave** (Bullet points)
    4. **Algoritmo Sugerido** (Si aplica, descríbelo paso a paso)

    TEXTO:
    {texto[:10000]} 
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generando contenido: {e}"

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
            
            # Extraer texto
            reader = PdfReader(ruta)
            texto_pdf = ""
            for page in reader.pages[:5]: 
                texto_pdf += page.extract_text() or ""
        except:
            contenido_bytes = None
            texto_pdf = ""

        # GENERAR CONTENIDO
        if "CONECTADO" in ESTADO_CEREBRO:
            analisis_texto = analizar_con_ia(texto_pdf, archivo)
            infografia_texto = "✅ IA Activa"
            resumen_texto = "Análisis generado por IA."
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
