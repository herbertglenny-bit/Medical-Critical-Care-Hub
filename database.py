import os

# CONFIGURACIÓN
# Carpeta donde buscar los PDFs. Pon "." para buscar en la raíz.
CARPETA_PDFS = "." 

def generar_biblioteca_automatica():
    biblioteca = []
    
    # 1. Verificar si hay archivos
    if not os.path.exists(CARPETA_PDFS):
        return []

    # 2. Buscar todos los PDFs
    archivos = sorted([f for f in os.listdir(CARPETA_PDFS) if f.lower().endswith('.pdf')])

    for archivo in archivos:
        # Título automático basado en el nombre del archivo
        # Ejemplo: "guia_sepsis.pdf" -> "Guia Sepsis"
        titulo_limpio = archivo.replace(".pdf", "").replace("_", " ").replace("-", " ").title()

        # Intentar leer el archivo para que sea descargable
        try:
            with open(os.path.join(CARPETA_PDFS, archivo), "rb") as f:
                contenido_bytes = f.read()
        except:
            contenido_bytes = None

        # --- AQUÍ ES DONDE OCURRIRÍA LA MAGIA DE LA IA ---
        # En un futuro, aquí llamaríamos a la API para que lea el texto.
        # Por ahora, generamos una plantilla automática.
        
        analisis_automatico = f"""
# Análisis de: {titulo_limpio}

## 📄 Resumen Automático
El documento **"{titulo_limpio}"** ha sido cargado correctamente en el sistema. 

## 🤖 Estado del Análisis
El archivo está listo para ser procesado. Para obtener el resumen clínico detallado y los puntos clave, es necesario activar la conexión con el modelo de Inteligencia Artificial.

## 🔗 Acciones
* Puedes visualizar el PDF original pulsando en el botón de la izquierda.
* El análisis de contenido se generará cuando el servicio de IA esté disponible.
"""

        infografia_automatica = f"""
# Info
**Archivo:** {archivo}
**Estado:** ✅ Cargado
"""

        # Crear el elemento para la web
        item = {
            "id": archivo,
            "titulo": titulo_limpio,
            "sociedad": "Documento PDF",
            "especialidad": "Medicina Intensiva",
            "anio": "2024",
            "resumen": f"Documento: {titulo_limpio}",
            "url_fuente": "",     # Se queda vacío
            "pdf_source": None,   # Se queda vacío
            "pdf_bytes": contenido_bytes, # ¡IMPORTANTE! Aquí va el archivo real
            "analisis": analisis_automatico,
            "infografia": infografia_automatica
        }
        
        biblioteca.append(item)

    return biblioteca

# Ejecutar
library = generar_biblioteca_automatica()
