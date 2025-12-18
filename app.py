from flask import Flask, render_template

# Creamos la aplicación
app = Flask(__name__)

# Esta es la ruta principal (cuando entras a la web)
@app.route('/')
def home():
    # Aquí le decimos: "Busca en la carpeta templates el archivo index.html y muéstralo"
    return render_template('index.html')

# Arrancamos el servidor
if __name__ == '__main__':
    app.run(debug=True, port=5000)
