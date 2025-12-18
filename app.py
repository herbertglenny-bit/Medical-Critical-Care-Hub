import streamlit as st
import streamlit.components.v1 as components

# 1. Configuración básica de la página para que ocupe todo el ancho
st.set_page_config(page_title="Estación Médica IA", layout="wide")

# 2. Leemos tu archivo HTML (el diseño nuevo)
# Asegúrate de que la ruta coincida con donde guardaste el archivo
try:
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        html_code = f.read()

    # 3. Lo mostramos en pantalla
    # height=1000 asegura que se vea alto y scrolling=True permite bajar si es necesario
    components.html(html_code, height=1000, scrolling=True)

except FileNotFoundError:
    st.error("No encuentro el archivo 'templates/index.html'. Revisa que la carpeta 'templates' exista y el archivo esté dentro.")
