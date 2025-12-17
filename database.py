# AQUÍ SE GUARDAN LAS GUÍAS PUBLICADAS
# Copia y pega los bloques generados por el Admin al final de esta lista.

# BASE DE DATOS DE GUÍAS MÉDICAS

library = [
    # --- GUÍA 1: DEMO ---
    {
        "id": "demo_001",
        "titulo": "Ejemplo: Surviving Sepsis Campaign 2021",
        "sociedad": "SCCM / ESICM",
        "especialidad": "Medicina Intensiva",
        "anio": "2021",
        "resumen": "Guía internacional para el manejo de la sepsis y shock séptico.",
        "url_fuente": "",
        "pdf_source": None,
        "pdf_bytes": None,
        "analisis": """
# Ejemplo de Análisis
Este es un texto de ejemplo para verificar que el sistema funciona.
""",
        "infografia": """
# Ejemplo de Infografía
Este es un texto de ejemplo.
"""
    },

    # --- GUÍA 2: PADIS 2018 ---
    {
        "id": "clinical_practice_gu",
        "titulo": "Clinical Practice Guidelines for the Prevention and Management of Pain, Agitation/Sedation, Delirium, Immobility, and Sleep Disruption in Adult Patients in the ICU",
        "sociedad": "Society of Critical Care Medicine",
        "especialidad": "Medicina Intensiva",
        "anio": "2018",
        "resumen": "Estas guías actualizan y expanden las directrices de 2013 para el manejo del dolor, agitación, sedación y delirio en pacientes adultos en la UCI.",
        "url_fuente": "",
        "pdf_source": None,
        "pdf_bytes": None,
        "analisis": """Como Médico Intensivista Senior, he realizado un análisis exhaustivo de las Guías PADIS 2018.

# Análisis GPC: Manejo de PADIS en UCI (2018)

## 1. Ficha Técnica
* **Título:** Clinical Practice Guidelines for PADIS.
* **Publicación:** 2018.
* **Objetivo:** Actualizar manejo de Dolor, Agitación, Delirio, Inmovilidad y Sueño.

## 2. Puntos Clave
* **Analgesia-First:** Tratar el dolor antes de sedar.
* **Sedación Ligera:** Preferir Propofol/Dexmedetomidina sobre Benzodiacepinas.
* **Delirio:** No usar antipsicóticos de rutina para prevención.

## 3. Algoritmo Bedside

```mermaid
graph TD
    A[Evaluar PADIS] --> B{Dolor?}
    B -- Sí --> C[Tratar Dolor (Opioides +/- Adyuvantes)]
    B -- No --> D{Agitación?}
    C --> D
    D -- Sí --> E[Sedación Ligera (RASS -2 a +1)]
    E --> F{Delirio?}
    F -- Sí --> G[Manejo No Farmacológico]
Explicación del Algoritmo: El diagrama anterior muestra el flujo de decisión clínica priorizando el control del dolor y manteniendo al paciente despierto (sedación ligera).

4. Conclusión
La guía enfatiza un enfoque integral y humanizado, reduciendo la sedación profunda y promoviendo la movilidad temprana. """, "infografia": """# Guía Rápida: Manejo PADIS (2018)

🚦 Semáforo
🟢 Hacer (Verde)
Evaluar dolor rutinariamente.

Usar sedación ligera.

Movilización temprana.

🔴 Evitar (Rojo)
Benzodiacepinas rutinarias.

Antipsicóticos para prevención de delirio.

Sueño inducido solo por fármacos.

💡 Mensaje Clave
Priorizar el confort (analgesia) y mantener al paciente interactivo facilita la recuperación y reduce el delirio. """ },

# --- GUÍA 3: ESICM SHOCK 2025 ---
{
    "id": "esicm_guidelines_on_",
    "titulo": "ESICM guidelines on circulatory shock and hemodynamic monitoring 2025",
    "sociedad": "ESICM",
    "especialidad": "Medicina Intensiva",
    "anio": "2025",
    "resumen": "Guías ESICM para el diagnóstico del shock y monitorización hemodinámica.",
    "url_fuente": "",
    "pdf_source": None,
    "pdf_bytes": None,
    "analisis": """Aquí tienes el análisis de las guías ESICM 2025.
Análisis ESICM 2025: Shock Circulatorio
1. Novedades
Relleno Capilar (TRC): Se recomienda explícitamente como monitorización de perfusión.

Individualización: Objetivos de presión arterial (MAP) según el paciente (ej. HTA crónica vs Trauma).

Riesgo de Fluidos: Evaluar el peligro de sobrecarga antes de dar más líquidos.

2. Algoritmo de Manejo
Fragmento de código

graph TD
    A[Shock Circulatorio] --> B{Hipoperfusión?}
    B -- Sí --> C[Ecocardiografía Precoz]
    C --> D[Definir Tipo de Shock]
    D --> E[Fluidoterapia Guiada por Respuesta]
    E --> F[Vasopresores si MAP bajo]
Explicación del Algoritmo:

Identificar signos clínicos de hipoperfusión (Lactato, TRC, Mottling).

Usar Eco para filiar la causa.

Administrar fluidos SOLO si hay respuesta positiva y bajo riesgo.

3. Puntos de Aprendizaje
El lactato no es el único objetivo; mirar la microcirculación.

Usar pruebas dinámicas (levantar piernas) antes de poner suero. """, "infografia": """# ESICM Shock 2025

🚦 Recomendaciones
🟢 Recomendado
Test de elevación pasiva de piernas.

Ecocardiografía como primera línea.

Objetivos de PAM individualizados.

🔴 No Recomendado
Usar PVC como objetivo de reanimación.

Fluidos sin evaluar respuesta previa.

📊 Dato Clave
El Tiempo de Relleno Capilar es una herramienta clínica potente y validada para guiar la reanimación. """ } ]
