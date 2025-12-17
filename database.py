import os

# ==========================================
# 1. PEGA TU CLAVE AQUÍ (SIN BORRAR LAS COMILLAS)
# ==========================================
GEMINI_API_KEY = "AIzaSyBy9wai4pEyFCGQUiALSCzqYMOSj2foTjM"

CARPETA_PDFS = "." 

# ==========================================
# 2. DIAGNÓSTICO DE ERRORES (CHIVATO)
# ==========================================
ESTADO_CEREBRO = "Iniciando..."
ERROR_DETALLE = ""

try:
    import google.generativeai as genai
    from pypdf import PdfReader
    
    # Verificamos si la clave tiene formato correcto
    if "AIza" not in GEMINI_API_KEY:
        ESTADO_CEREBRO = "❌ ERROR DE CLAVE"
        ERROR_DETALLE = "La clave no empieza por 'AIza'. Sigues teniendo el texto de ejemplo o la has copiado mal."
    else:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        ESTADO_CEREBRO = "✅ CONECTADO"

except ImportError:
    ESTADO_CEREBRO = "❌ ERROR DE INSTALACIÓN"
    ERROR_DETALLE = "El servidor no encuentra la librería 'google-generativeai'. Revisa tu archivo requirements.txt y reinicia la app."
except Exception as e:
    ESTADO_CEREBRO = "❌ ERROR DESCONOCIDO"
    ERROR_DETALLE = str(e)


# ==========================================
# 3. MOTOR DE ANÁLISIS
# ==========================================

def analizar_con_ia(texto, archivo):
    if "ERROR" in ESTADO_CEREBRO:
        return None 
    
    prompt = f"Eres un experto médico. Resume este PDF ({archivo}) en 3 puntos clave: \n\n {texto[:5000]}"
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
        # Leer PDF
        try:
            ruta = os.path.join(CARPETA_PDFS, archivo)
            with open(ruta, "rb") as f:
                contenido_bytes = f.read()
                
            # Extraer texto básico para enviar a la IA
            reader = PdfReader(ruta)
            texto_pdf = ""
            for page in reader.pages[:5]: # Solo primeras 5 pág para ir rápido
                texto_pdf += page.extract_text() or ""
        except:
            contenido_bytes = None
            texto_pdf = ""

        # GENERAR CONTENIDO
        if "CONECTADO" in ESTADO_CEREBRO:
            # Si todo va bien, preguntamos a la IA
            analisis_texto = analizar_con_ia(texto_pdf, archivo)
            infografia_texto = f"✅ IA Activa. Procesado con éxito."
            resumen_texto = "Análisis generado por Inteligencia Artificial."
        else:
            # Si falla, MOSTRAMOS EL ERROR EN PANTALLA
            analisis_texto = f"""
# ⚠️ DIAGNÓSTICO DE FALLO
El sistema no puede analizar el PDF por la siguiente razón:

### Estado: {ESTADO_CEREBRO}
### Detalle: {ERROR_DETALLE}

**Solución:**
1. Si dice "Error de Instalación": Arregla requirements.txt
2. Si dice "Error de Clave": Revisa la variable GEMINI_API_KEY en database.py
"""
            infografia_texto = "❌ Sistema desconectado"
            resumen_texto = f"Error: {ESTADO_CEREBRO}"

        # Guardar
        item = {
            "id": archivo,
            "titulo": archivo.replace(".pdf", ""),
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
