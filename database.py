import os

# ==========================================
# 1. PEGA TU CLAVE AQUÍ (SIN BORRAR LAS COMILLAS)
# ==========================================
GEMINI_API_KEY = "AIzaSyBy9wai4pEyFCGQUiALSCzqYMOSj2foTjM" 

CARPETA_PDFS = "." 

# ==========================================
# 2. DIAGNÓSTICO DE CONEXIÓN
# ==========================================
ESTADO_CEREBRO = "Iniciando..."
ERROR_DETALLE = ""

try:
    import google.generativeai as genai
    from pypdf import PdfReader
    
    # Verificamos si la clave tiene formato correcto
    if "AIza" not in GEMINI_API_KEY:
        ESTADO_CEREBRO = "❌ ERROR DE CLAVE"
        ERROR_DETALLE = "La clave no empieza por 'AIza'. Revisa que la has pegado bien."
    else:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # --- CAMBIO IMPORTANTE AQUÍ ---
        # Usamos 'gemini-pro' que es el modelo más compatible actualmente.
        model = genai.GenerativeModel('gemini-pro')
        ESTADO_CEREBRO = "✅ CONECTADO"

except ImportError:
    ESTADO_CEREBRO = "❌ ERROR DE INSTALACIÓN"
    ERROR_DETALLE = "Faltan librerías. Revisa requirements.txt."
except Exception as e:
    ESTADO_CEREBRO = "❌ ERROR DESCONOCIDO"
    ERROR_DETALLE = str(e)


# ==========================================
# 3. MOTOR DE ANÁLISIS
# ==========================================

def analizar_con_ia(texto, archivo):
    if "ERROR" in ESTADO_CEREBRO:
        return None 
    
    # Prompt mejorado para el médico
    prompt = f"""
    Actúa como un médico intensivista experto.
    Analiza el siguiente texto extraído de un documento PDF ({archivo}).
    
    Genera un resumen en formato Markdown con estos 3 apartados:
    1. **Título y Año** (si se detecta).
    2. **Resumen Ejecutivo**: De qué trata el documento en 2 líneas.
    3. **Puntos Clave**: 3 o 4 bullets points con lo más importante.

    TEXTO DEL PDF:
    {texto[:8000]} 
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error al hablar con Google: {e}"

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
            
            # Extraer texto para la IA
            reader = PdfReader(ruta)
            texto_pdf = ""
            # Leemos primeras 4 páginas para no saturar
            for page in reader.pages[:4]: 
                texto_pdf += page.extract_text() or ""
        except:
            contenido_bytes = None
            texto_pdf = ""

        # GENERAR CONTENIDO
        if "CONECTADO" in ESTADO_CEREBRO:
            # Preguntamos a la IA
            analisis_texto = analizar_con_ia(texto_pdf, archivo)
            infografia_texto = "✅ Procesado con IA (Gemini Pro)"
            resumen_texto = "Análisis generado automáticamente."
        else:
            # Si falla, mostramos por qué
            analisis_texto = f"""
# ⚠️ ERROR DE CONEXIÓN
No se ha podido generar el análisis.

**Causa:** {ESTADO_CEREBRO}
**Detalle:** {ERROR_DETALLE}
"""
            infografia_texto = "❌ Sin conexión"
            resumen_texto = "Error de sistema."

        # Guardar
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
