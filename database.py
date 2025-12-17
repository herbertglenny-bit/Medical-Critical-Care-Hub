import os
import google.generativeai as genai
from pypdf import PdfReader

# ==========================================
# 1. TU CLAVE AQUÍ
# ==========================================
GEMINI_API_KEY = "AIzaSyBy9wai4pEyFCGQUiALSCzqYMOSj2foTjM"

CARPETA_PDFS = "." 

# ==========================================
# 2. CONEXIÓN INTELIGENTE
# ==========================================
ESTADO_CEREBRO = "Iniciando..."
model = None

try:
    if "AIza" not in GEMINI_API_KEY:
        ESTADO_CEREBRO = "❌ ERROR DE CLAVE"
    else:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Buscamos el mejor modelo disponible automáticamente
        modelo_elegido = None
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    if 'gemini' in m.name:
                        modelo_elegido = m.name
                        break 
        except:
            pass
        
        if not modelo_elegido: modelo_elegido = 'gemini-1.5-flash'
            
        print(f"Modelo IA activado: {modelo_elegido}")
        model = genai.GenerativeModel(modelo_elegido)
        ESTADO_CEREBRO = "✅ CONECTADO"

except Exception as e:
    ESTADO_CEREBRO = f"❌ ERROR: {str(e)}"

# ==========================================
# 3. EL PROMPT "INTENSIVISTA SENIOR"
# ==========================================

def analizar_con_ia(texto, archivo):
    if "ERROR" in ESTADO_CEREBRO:
        return None, None
    
    # Este es el prompt potente que diseñamos al principio
    prompt = f"""
    Actúa como un Médico Intensivista Senior y Experto en Educación Médica.
    Analiza el siguiente texto extraído de un PDF: "{archivo}".

    Genera una respuesta dividida en dos partes exactas separadas por la palabra "---SEPARADOR---".

    PARTE 1: EL ANÁLISIS DETALLADO (Formato Markdown)
    Debe tener esta estructura obligatoria:
    1. # Ficha Técnica
       - Título completo, Sociedad, Año y Objetivo principal en 1 línea.
    2. # Análisis Delta (Novedades vs Práctica Anterior)
       - Explica qué cambia respecto a guías previas.
       - Qué es nuevo y qué queda obsoleto.
    3. # Algoritmo Bedside
       - GENERA CÓDIGO MERMAID (graph TD) que represente el flujo de decisión clínica del documento.
       - Añade una breve explicación del algoritmo debajo.
    4. # Rincón del Residente
       - 3 a 5 "Learning Points" o perlas clínicas para llevar a casa.
    5. # Incertidumbre
       - Qué evidencia falta o es débil según el documento.

    PARTE 2: LA INFOGRAFÍA (Formato Markdown breve)
    Estructura de Semáforo:
    - # Semáforo de Recomendaciones
    - 🟢 Hacer (Recomendaciones fuertes).
    - 🟡 Considerar (Recomendaciones condicionales).
    - 🔴 Evitar (No recomendado / Dañino).
    - 📊 Dato Clave (Un número o porcentaje impactante del texto).

    ---SEPARADOR---
    (Aquí empieza la parte 2)

    TEXTO A ANALIZAR:
    {texto[:30000]} 
    """
    
    try:
        response = model.generate_content(prompt)
        texto_completo = response.text
        
        # Separamos el Análisis de la Infografía usando nuestra "marca"
        if "---SEPARADOR---" in texto_completo:
            partes = texto_completo.split("---SEPARADOR---")
            analisis = partes[0].strip()
            infografia = partes[1].strip()
        else:
            analisis = texto_completo
            infografia = "# Error de formato\nLa IA no generó el separador."
            
        return analisis, infografia
        
    except Exception as e:
        return f"Error IA: {e}", "Error visual"

# ==========================================
# 4. MOTOR DE GENERACIÓN
# ==========================================

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
            
            # Extraer texto (leemos más páginas para tener mejor contexto)
            reader = PdfReader(ruta)
            texto_pdf = ""
            for page in reader.pages[:15]: 
                texto_pdf += page.extract_text() or ""
        except:
            contenido_bytes = None
            texto_pdf = ""

        # GENERAR CONTENIDO
        titulo = archivo.replace(".pdf", "").replace("_", " ").title()
        
        if "CONECTADO" in ESTADO_CEREBRO:
            print(f"🧠 Analizando {archivo} con IA...")
            analisis_texto, infografia_texto = analizar_con_ia(texto_pdf, archivo)
            resumen_texto = "Análisis completo generado por IA."
        else:
            analisis_texto = f"# Error\n{ESTADO_CEREBRO}"
            infografia_texto = "❌ Offline"
            resumen_texto = "Error de conexión."

        item = {
            "id": archivo,
            "titulo": titulo,
            "sociedad": "Auto-Detectada",
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
