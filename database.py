import os

# --- CONFIGURACIÓN ---
# Si subiste el PDF a la raíz (junto a main.py), usa "."
# Si lograste crear la carpeta, usa "pdfs_guias"
CARPETA_PDFS = "." 

def generar_biblioteca_automatica():
    biblioteca = []
    
    # Si la carpeta no existe, devolvemos lista vacía para no romper nada
    if not os.path.exists(CARPETA_PDFS):
        return []

    # Buscamos todos los PDFs
    archivos = [f for f in os.listdir(CARPETA_PDFS) if f.lower().endswith('.pdf')]

    for archivo in archivos:
        # Leemos el archivo real
        try:
            ruta = os.path.join(CARPETA_PDFS, archivo)
            with open(ruta, "rb") as f:
                contenido_pdf = f.read()
        except:
            contenido_pdf = None

        # --- AQUÍ ESTÁ EL TRUCO ---
        # Definimos valores por defecto (genéricos)
        titulo = archivo.replace(".pdf", "").replace("_", " ").title()
        resumen = "Documento cargado automáticamente."
        analisis = "# Análisis Pendiente\nConecta una API para generar esto automáticamente."
        infografia = "# Sin datos"

        # --- RECUPERACIÓN MANUAL DE TUS ANÁLISIS ---
        # Si el nombre del archivo contiene palabras clave, inyectamos el texto bueno.
        
        # CASO 1: GUÍA PADIS 2018
        if "padis" in archivo.lower() or "pain" in archivo.lower():
            titulo = "Guía PADIS 2018 (Dolor, Agitación, Delirio)"
            resumen = "Guías de Práctica Clínica para la Prevención y Manejo del Dolor, Agitación/Sedación, Delirio, Inmovilidad y Alteración del Sueño en Adultos en UCI."
            analisis = """
# Análisis GPC: Manejo de PADIS en UCI (2018)

## 1. Ficha Técnica
* **Título:** Clinical Practice Guidelines for PADIS.
* **Publicación:** 2018.
* **Objetivo:** Actualizar manejo de Dolor, Agitación, Delirio, Inmovilidad y Sueño.

## 2. Puntos Clave
* **Analgesia-First:** Tratar el dolor antes de sedar.
* **Sedación Ligera:** Preferir Propofol/Dexmedetomidina sobre Benzodiacepinas.
* **Delirio:** No usar antipsicóticos de rutina para prevención.

## 3. Algoritmo Bedside (Flujo de Decisión)
1. **[INICIO: Evaluar PADIS]**
   ↓
2. **¿Tiene Dolor?**
   ├── **SÍ:** Tratar Dolor (Opioides +/- Adyuvantes)
   └── **NO:** Pasar a evaluar Agitación
   ↓
3. **¿Tiene Agitación?**
   ├── **SÍ:** Iniciar Sedación Ligera (Objetivo RASS -2 a +1)
   └── **NO:** Continuar monitorización
   ↓
4. **¿Tiene Delirio?**
   ├── **SÍ:** Manejo No Farmacológico (Reorientación, Sueño)
   └── **NO:** Evaluar Movilidad Temprana
"""
            infografia = """
# Semáforo PADIS
### 🟢 Hacer
* Evaluar dolor rutinariamente.
* Usar sedación ligera.
### 🔴 Evitar
* Benzodiacepinas rutinarias.
* Antipsicóticos preventivos.
"""

        # CASO 2: GUÍA ESICM SHOCK 2025
        elif "esicm" in archivo.lower() or "shock" in archivo.lower():
            titulo = "Guías ESICM 2025: Shock Circulatorio"
            resumen = "Recomendaciones para el diagnóstico del shock y monitorización hemodinámica en pacientes críticos."
            analisis = """
# Análisis ESICM 2025: Shock Circulatorio

## 1. Novedades
* **Relleno Capilar (TRC):** Se recomienda explícitamente como monitorización de perfusión.
* **Individualización:** Objetivos de presión arterial (MAP) según el paciente.
* **Riesgo de Fluidos:** Evaluar el peligro de sobrecarga antes de dar más líquidos.

## 2. Algoritmo de Manejo
1. **[SOSPECHA DE SHOCK]** → ¿Signos de Hipoperfusión?
2. **Diagnóstico:** Usar Ecocardiografía Precoz.
3. **Resucitación:** Fluidos SOLO si hay respuesta positiva y bajo riesgo.
"""
            infografia = """
# ESICM Shock 2025
### 🟢 Recomendado
* Test de elevación pasiva de piernas.
* Ecocardiografía como primera línea.
### 🔴 No Recomendado
* Usar PVC como objetivo de reanimación.
"""

        # --- FIN DEL TRUCO ---

        # Creamos el objeto final
        item = {
            "id": archivo,
            "titulo": titulo,
            "sociedad": "Auto-Detectada",
            "especialidad": "UCI",
            "anio": "2024",
            "resumen": resumen,
            "url_fuente": "",
            "pdf_source": None,
            "pdf_bytes": contenido_pdf,
            "analisis": analisis,
            "infografia": infografia
        }
        biblioteca.append(item)

    return biblioteca

# Ejecutamos la función
library = generar_biblioteca_automatica()
