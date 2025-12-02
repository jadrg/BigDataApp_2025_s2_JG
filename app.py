from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from dotenv import load_dotenv
import os
from werkzeug.utils import secure_filename
from datetime import datetime

# Helpers correctos (IMPORTANTE)
from Helpers.mongoDB import MongoDB
from Helpers.elastic import ElasticSearch
from Helpers.funciones import Funciones
from Helpers.webScraping import WebScraping
from Helpers.OCRtoElastic import OCRtoElastic   # ← IMPORTE CORRECTO

# ==================== CONFIGURACIÓN ====================
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_super_secreta_12345')

# MongoDB
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB')
MONGO_COLECCION = os.getenv('MONGO_COLECCION', 'usuario_roles')

# Elastic
ELASTIC_CLOUD_URL = os.getenv('ELASTIC_CLOUD_URL')
ELASTIC_API_KEY = os.getenv('ELASTIC_API_KEY')
ELASTIC_INDEX_DEFAULT = os.getenv('ELASTIC_INDEX_DEFAULT', 'index_normatividad')

# Metadatos
VERSION_APP = "1.2.0"
CREATOR_APP = "JaderAGO"

# Conexiones
mongo = MongoDB(MONGO_URI, MONGO_DB)
elastic = ElasticSearch(ELASTIC_CLOUD_URL, ELASTIC_API_KEY)

# OCR → ElasticSearch
ocr = OCRtoElastic(
    elastic_instance=elastic,
    index_name="index_normatividad"
)

# ==================== RUTAS ====================

@app.route('/')
def landing():
    return render_template('landing.html', version=VERSION_APP, creador=CREATOR_APP)

@app.route('/about')
def about():
    return render_template('about.html', version=VERSION_APP, creador=CREATOR_APP)

# ==================== BUSCADOR ELASTIC ====================

@app.route('/buscador')
def buscador():
    return render_template('buscador.html', version=VERSION_APP, creador=CREATOR_APP)

@app.route('/buscar-elastic', methods=['POST'])
def buscar_elastic():
    try:
        data = request.get_json()
        texto_buscar = data.get('texto', '').strip()

        if not texto_buscar:
            return jsonify({'success': False, 'error': 'Texto requerido'}), 400

        query = {
            "query": {
                "match": {
                    "texto_ocr": texto_buscar
                }
            }
        }

        resultado = elastic.buscar(
            index=ELASTIC_INDEX_DEFAULT,
            query=query,
            size=50
        )
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== LOGIN / USUARIOS ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        password = request.form.get('password')

        user_data = mongo.validar_usuario(usuario, password, MONGO_COLECCION)

        if user_data:
            session['usuario'] = usuario
            session['permisos'] = user_data.get('permisos', {})
            session['logged_in'] = True
            flash('¡Bienvenido!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')

    return render_template('login.html')

@app.route('/listar-usuarios')
def listar_usuarios():
    try:
        usuarios = mongo.listar_usuarios(MONGO_COLECCION)
        for usuario in usuarios:
            usuario['_id'] = str(usuario['_id'])
        return jsonify(usuarios)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== ELASTICSEARCH ====================

@app.route('/gestor_elastic')
def gestor_elastic():
    if not session.get('logged_in'):
        flash('Inicia sesión', 'warning')
        return redirect(url_for('login'))

    permisos = session.get('permisos', {})
    if not permisos.get('admin_elastic'):
        flash('Sin permisos', 'danger')
        return redirect(url_for('admin'))

    return render_template(
        'gestor_elastic.html',
        usuario=session.get('usuario'),
        permisos=permisos,
        version=VERSION_APP,
        creador=CREATOR_APP
    )

@app.route('/listar-indices-elastic')
def listar_indices_elastic():
    try:
        return jsonify(elastic.listar_indices())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/procesar-webscraping-elastic', methods=['POST'])
def procesar_webscraping_elastic():
    try:
        data = request.get_json()
        url = data.get('url')
        index = data.get('index')

        if not url or not index:
            return jsonify({'success': False, 'error': 'URL e índice requeridos'}), 400

        scraper = WebScraping(dominio_base=url.rsplit('/', 1)[0] + '/')

        carpeta_upload = 'static/uploads'
        Funciones.crear_carpeta(carpeta_upload)
        Funciones.borrar_contenido_carpeta(carpeta_upload)

        json_path = os.path.join(carpeta_upload, 'links.json')
        resultado = scraper.extraer_todos_los_links(url, json_path, ['pdf'], 30)

        resultado_descarga = scraper.descargar_pdfs(json_path, carpeta_upload)

        scraper.close()

        return jsonify({
            'success': True,
            'total_links': resultado['total_links'],
            'descargados': resultado_descarga.get('descargados', 0),
            'errores': resultado_descarga.get('errores', [])
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ADMIN ====================

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        flash('Inicia sesión', 'warning')
        return redirect(url_for('login'))

    return render_template(
        'admin.html',
        usuario=session.get('usuario'),
        permisos=session.get('permisos')
    )

# ================= MAIN ====================

if __name__ == '__main__':
    Funciones.crear_carpeta('static/uploads')

    print("\n===== VERIFICANDO CONEXIONES =====\n")

    print("MongoDB:", "OK" if mongo.test_connection() else "ERROR")
    print("ElasticSearch:", "OK" if elastic.test_connection() else "ERROR")

    app.run(debug=True, host='0.0.0.0', port=5000)