import os

# --- CONFIGURACIÓN ---
# Nombre de la carpeta donde pondrás los PDFs
CARPETA_PDFS = "pdfs_guias"

def generar_biblioteca_automatica():
    biblioteca = []

    # Crear carpeta si no existe
    if not os.path.exists(CARPETA_PDFS):
        os.makedirs(CARPETA_PDFS)
        return [] # Retorna vacío por ahora

    # Buscar archivos PDF
    archivos = [f for f in os.listdir(CARPETA_PDFS) if f.lower().endswith('.pdf')]

    for archivo in archivos:
        ruta_completa = os.path.join(CARPETA_PDFS, archivo)
        
        # Intentar leer el PDF
        try:
            with open(ruta_completa, "rb") as f:
                contenido_pdf = f.read()
        except:
            contenido_pdf = None

        # Crear el objeto de la guía automáticamente
        item = {
            "id": archivo,
            "titulo": archivo.replace(".pdf", "").replace("_", " ").title(),
            "sociedad": "Documento Local", 
            "especialidad": "Medicina Intensiva",
            "anio": "2024",
            "resumen": f"Archivo cargado automáticamente: {archivo}",
            "url_fuente": "",
            "pdf_source": None,
            "pdf_bytes": contenido_pdf, # Aquí va el archivo real
            
            # Texto por defecto (ya que no hay IA conectada escribiéndolo)
            "analisis": f"""
# Archivo Detectado: {archivo}
Este documento se ha cargado automáticamente desde tu carpeta local.
El análisis detallado por IA aparecerá aquí cuando conectes la API.
""",
            "infografia": f"""
# Estado del Archivo
* **Nombre:** {archivo}
* **Carga:** Exitosa
"""
        }
        biblioteca.append(item)

    return biblioteca

# --- ESTA LÍNEA ES IMPORTANTE ---
# Al ejecutar el programa, 'library' se llena sola escaneando la carpeta.
library = generar_biblioteca_automatica()
