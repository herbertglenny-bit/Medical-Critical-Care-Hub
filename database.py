import os
import google.generativeai as genai
from pypdf import PdfReader

# ==========================================
# 1. CONFIGURACIÓN DE LA IA (GEMINI)
# ==========================================
# BORRA LO QUE HAYA ENTRE LAS COMILLAS Y PEGA TU CLAVE:
GEMINI_API_KEY = "AIzaSyBy9wai4pEyFCGQUiALSCzqYMOSj2foTjM" 

CARPETA_PDFS = "." 

# --- ZONA DE DIAGNÓSTICO ---
print(f"--- DIAGNÓSTICO DE CLAVE ---")
print(f"Longitud de la clave detectada: {len(GEMINI_API_KEY)}")
if GEMINI_API_KEY.startswith("TU_CLAVE"):
    print("❌ ERROR: Sigues teniendo el texto de ejemplo.")
elif " " in GEMINI_API_KEY:
    print("❌ ERROR: Hay espacios en blanco dentro de las comillas.")
else:
    print("✅ La clave parece correcta (formato válido).")
print(f"----------------------------")

TIENE_CEREBRO = False
try:
    if len(GEMINI_API_KEY) > 30 and not " " in GEMINI_API_KEY: 
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        TIENE_CEREBRO = True
        print("🧠 CEREBRO ACTIVADO: Conexión lista.")
    else:
        print("🧠 CEREBRO APAGADO: La clave no cumple los requisitos.")
except Exception as e:
    print(f"❌ Error técnico al conectar: {e}")

# ==========================================
# A PARTIR DE AQUÍ NO TOQUES NADA
# ==========================================# ==========================================
# 2. FUNCIONES DE LECTURA Y ANÁLISIS
# ==========================================

def leer_texto_pdf(ruta_pdf):
    """Extrae el texto de las primeras páginas del PDF."""
    texto_completo = ""
    try:
        reader = PdfReader(ruta_pdf)
        # Leemos solo las primeras 10 páginas para no saturar y ser rápidos
        paginas_a_leer = min(len(reader.pages), 10) 
        for i in range(paginas_a_leer):
            texto = reader.pages[i].extract_text()
            if texto:
                texto_completo += texto + "\n"
    except Exception as e:
        print(f"Error leyendo PDF: {e}")
    return texto_completo

def analizar_con_ia(texto_pdf, nombre_archivo):
    """Envía el texto a Gemini y pide el análisis."""
    if not TIENE_CEREBRO:
        return None, None # Sin clave, no hay análisis real

    prompt = f"""
    Actúa como un Médico Intensivista Senior. Analiza el siguiente texto extraído de una guía clínica ({nombre_archivo}).
    
    Genera dos salidas separadas:
    1. 'ANALISIS': Un resumen estructurado en Markdown con: Título oficial, Año, Mensajes Clave y un Algoritmo explicativo en texto (lista numerada).
    2. 'INFOGRAFIA': Un resumen visual muy breve tipo "Semáforo" (Verde/Rojo) con emojis.

    Texto del PDF:
    {texto_pdf[:15000]} # Limitamos caracteres por seguridad
    """

    try:
        response = model.generate_content(prompt)
        respuesta = response.text
        
        # Un pequeño truco para separar el texto si Gemini lo devuelve todo junto
        # (Esto es básico, en producción se refinaría)
        analisis = respuesta
        infografia = "Ver sección de puntos clave en el análisis."
        
        return analisis, infografia
    except Exception as e:
        print(f"Error conectando con Gemini: {e}")
        return None, None

# ==========================================
# 3. MOTOR AUTOMÁTICO
# ==========================================

def generar_biblioteca_automatica():
    biblioteca = []
    
    if not os.path.exists(CARPETA_PDFS):
        return []

    archivos = sorted([f for f in os.listdir(CARPETA_PDFS) if f.lower().endswith('.pdf')])

    for archivo in archivos:
        print(f"Procesando: {archivo}...")
        
        # 1. Leer el archivo físico para descarga
        ruta_completa = os.path.join(CARPETA_PDFS, archivo)
        try:
            with open(ruta_completa, "rb") as f:
                contenido_bytes = f.read()
        except:
            contenido_bytes = None

        # 2. Extraer texto del PDF
        texto_del_pdf = leer_texto_pdf(ruta_completa)

        # 3. Preguntar a la IA (Si tenemos clave)
        analisis_ia, info_ia = analizar_con_ia(texto_del_pdf, archivo)

        # 4. Preparar los textos finales
        titulo = archivo.replace(".pdf", "").replace("_", " ").title()
        
        if analisis_ia:
            # Si la IA respondió
            resumen_final = "Análisis generado automáticamente por Gemini AI."
            contenido_analisis = analisis_ia
            contenido_info = info_ia
        else:
            # Si NO hay IA configurada
            resumen_final = "Carga automática (IA no activa)."
            contenido_analisis = f"""
# Análisis Pendiente para {titulo}
⚠️ **Falta la API Key de Gemini**

Para que yo (el código) pueda leer y analizar este PDF automáticamente como hacía el chat, necesitas configurar tu `GEMINI_API_KEY` en el archivo `database.py`.

Mientras tanto, he cargado el archivo para que puedas abrirlo.
"""
            contenido_info = "# Sin IA"

        # 5. Guardar en la lista
        item = {
            "id": archivo,
            "titulo": titulo,
            "sociedad": "Auto-Detectada",
            "especialidad": "UCI",
            "anio": "2024",
            "resumen": resumen_final,
            "url_fuente": "",
            "pdf_source": None,
            "pdf_bytes": contenido_bytes,
            "analisis": contenido_analisis,
            "infografia": contenido_info
        }
        biblioteca.append(item)

    return biblioteca

library = generar_biblioteca_automatica()
