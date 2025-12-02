from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from dotenv import load_dotenv
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from Helpers import MongoDB, ElasticSearch, Funciones, WebScraping, OCRtoElastic 

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_super_secreta_12345')

# Configuración MongoDB
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB')
MONGO_COLECCION = os.getenv('MONGO_COLECCION', 'usuario_roles')

# Configuración ElasticSearch Cloud
ELASTIC_CLOUD_URL = os.getenv('ELASTIC_CLOUD_URL')
ELASTIC_API_KEY = os.getenv('ELASTIC_API_KEY')
ELASTIC_INDEX_DEFAULT = os.getenv('ELASTIC_INDEX_DEFAULT', 'index_normatividad')

# Versión de la aplicación
VERSION_APP = "1.2.0"
CREATOR_APP = "JaderGO"

# Inicializar conexiones
mongo = MongoDB(MONGO_URI, MONGO_DB)
elastic = ElasticSearch(ELASTIC_CLOUD_URL, ELASTIC_API_KEY)

# OCR → ElasticSearch
ocr = OCRtoElastic(
    elastic_instance=elastic,
    index_name=ELASTIC_INDEX_DEFAULT)

# ==================== RUTAS ====================

@app.route('/')
def landing():
    return render_template('landing.html', version=VERSION_APP, creador=CREATOR_APP)

@app.route('/about')
def about():
    return render_template('about.html', version=VERSION_APP, creador=CREATOR_APP)

# ----------- Buscador Elastic -----------
@app.route('/buscador')
def buscador():
    return render_template('buscador.html', version=VERSION_APP, creador=CREATOR_APP)

@app.route('/buscar-elastic', methods=['POST'])
def buscar_elastic():
    try:
        data = request.get_json()
        texto_buscar = data.get('texto', '').strip()
        campo = 'texto'

        if not texto_buscar:
            return jsonify({'success': False, 'error': 'Texto de búsqueda es requerido'}), 400

        query_base = {
            "query": {
                "match": {campo: texto_buscar}
            }
        }

        aggs = {
            "cuentos_por_mes": {
                "date_histogram": {"field": "fecha_creacion", "calendar_interval": "month"}
            },
            "cuentos_por_autor": {
                "terms": {"field": "autor", "size": 10}
            }
        }

        resultado = elastic.buscar(
            index=ELASTIC_INDEX_DEFAULT,
            query=query_base,
            aggs=aggs,
            size=100
        )

        return jsonify(resultado)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ----------- Gestión de usuarios (MongoDB) -----------

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
            flash('¡Bienvenido! Inicio de sesión exitoso', 'success')
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

@app.route('/gestor_usuarios')
def gestor_usuarios():
    if not session.get('logged_in'):
        flash('Por favor, inicia sesión para acceder a esta página', 'warning')
        return redirect(url_for('login'))

    permisos = session.get('permisos', {})
    if not permisos.get('admin_Usuarios'):
        flash('No tiene permisos para gestionar usuarios', 'danger')
        return redirect(url_for('admin'))

    return render_template('gestor_usuarios.html',
                        usuario=session.get('usuario'),
                        permisos=permisos,
                        version=VERSION_APP,
                        creador=CREATOR_APP)

@app.route('/crear-usuario', methods=['POST'])
def crear_usuario():
    try:
        if not session.get('logged_in'):
            return jsonify({'success': False, 'error': 'No autorizado'}), 401

        permisos = session.get('permisos', {})
        if not permisos.get('admin_usuarios'):
            return jsonify({'success': False, 'error': 'No tiene permisos para crear usuarios'}), 403

        data = request.get_json()
        usuario = data.get('usuario')
        password = data.get('password')
        permisos_usuario = data.get('permisos', {})

        if not usuario or not password:
            return jsonify({'success': False, 'error': 'Usuario y contraseña requeridos'}), 400

        usuario_existente = mongo.obtener_usuario(usuario, MONGO_COLECCION)
        if usuario_existente:
            return jsonify({'success': False, 'error': 'El usuario ya existe'}), 400

        resultado = mongo.crear_usuario(usuario, password, permisos_usuario, MONGO_COLECCION)

        return jsonify({'success': True}) if resultado else jsonify({'success': False}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/actualizar-usuario', methods=['POST'])
def actualizar_usuario():
    try:
        if not session.get('logged_in'):
            return jsonify({'success': False, 'error': 'No autorizado'}), 401

        permisos = session.get('permisos', {})
        if not permisos.get('admin_usuarios'):
            return jsonify({'success': False, 'error': 'No tiene permisos para actualizar usuarios'}), 403

        data = request.get_json()
        usuario_original = data.get('usuario_original')
        datos_usuario = data.get('datos', {})

        if not usuario_original:
            return jsonify({'success': False, 'error': 'Usuario original requerido'}), 400

        usuario_existente = mongo.obtener_usuario(usuario_original, MONGO_COLECCION)
        if not usuario_existente:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

        nuevo_usuario = datos_usuario.get('usuario')
        if nuevo_usuario and nuevo_usuario != usuario_original:
            if mongo.obtener_usuario(nuevo_usuario, MONGO_COLECCION):
                return jsonify({'success': False, 'error': 'Ya existe otro usuario con ese nombre'}), 400

        resultado = mongo.actualizar_usuario(usuario_original, datos_usuario, MONGO_COLECCION)

        return jsonify({'success': True}) if resultado else jsonify({'success': False}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/eliminar-usuario', methods=['POST'])
def eliminar_usuario():
    try:
        if not session.get('logged_in'):
            return jsonify({'success': False, 'error': 'No autorizado'}), 401

        permisos = session.get('permisos', {})
        if not permisos.get('admin_usuarios'):
            return jsonify({'success': False, 'error': 'No tiene permisos para eliminar usuarios'}), 403

        data = request.get_json()
        usuario = data.get('usuario')

        if not usuario:
            return jsonify({'success': False, 'error': 'Usuario requerido'}), 400

        usuario_existente = mongo.obtener_usuario(usuario, MONGO_COLECCION)
        if not usuario_existente:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

        if usuario == session.get('usuario'):
            return jsonify({'success': False, 'error': 'No puede eliminarse a sí mismo'}), 400

        resultado = mongo.eliminar_usuario(usuario, MONGO_COLECCION)

        return jsonify({'success': True}) if resultado else jsonify({'success': False}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ----------- ElasticSearch (carga de documentos) -----------

@app.route('/gestor_elastic')
def gestor_elastic():
    if not session.get('logged_in'):
        flash('Por favor, inicia sesión para acceder a ElasticSearch', 'warning')
        return redirect(url_for('login'))

    permisos = session.get('permisos', {})
    if not permisos.get('admin_elastic'):
        flash('No tiene permisos para gestionar ElasticSearch', 'danger')
        return redirect(url_for('admin'))

    return render_template('gestor_elastic.html',
                        usuario=session.get('usuario'),
                        permisos=permisos,
                        version=VERSION_APP,
                        creador=CREATOR_APP)

@app.route('/listar-indices-elastic')
def listar_indices_elastic():
    try:
        if not session.get('logged_in'):
            return jsonify({'error': 'No autorizado'}), 401

        permisos = session.get('permisos', {})
        if not permisos.get('admin_elastic'):
            return jsonify({'error': 'No tiene permisos'}), 403

        return jsonify(elastic.listar_indices())

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ejecutar-query-elastic', methods=['POST'])
def ejecutar_query_elastic():
    try:
        if not session.get('logged_in'):
            return jsonify({'success': False, 'error': 'No autorizado'}), 401

        permisos = session.get('permisos', {})
        if not permisos.get('admin_elastic'):
            return jsonify({'success': False, 'error': 'No tiene permisos'}), 403

        data = request.get_json()
        query_json = data.get('query')

        if not query_json:
            return jsonify({'success': False, 'error': 'Query requerida'}), 400

        return jsonify(elastic.ejecutar_query(query_json))

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/cargar_doc_elastic')
def cargar_doc_elastic():
    if not session.get('logged_in'):
        flash('Por favor, inicia sesión', 'warning')
        return redirect(url_for('login'))

    permisos = session.get('permisos', {})
    if not permisos.get('admin_data_elastic'):
        flash('No tiene permisos', 'danger')
        return redirect(url_for('admin'))

    return render_template('documentos_elastic.html',
                        usuario=session.get('usuario'),
                        permisos=permisos,
                        version=VERSION_APP,
                        creador=CREATOR_APP)

# ----------- Web Scraping para Elastic -----------

@app.route('/procesar-webscraping-elastic', methods=['POST'])
def procesar_webscraping_elastic():
    try:
        if not session.get('logged_in'):
            return jsonify({'success': False, 'error': 'No autorizado'}), 401

        permisos = session.get('permisos', {})
        if not permisos.get('admin_data_elastic'):
            return jsonify({'success': False, 'error': 'No tiene permisos'}), 403

        data = request.get_json()
        url = data.get('url')
        extensiones_navegar = data.get('extensiones_navegar', 'aspx')
        tipos_archivos = data.get('tipos_archivos', 'pdf')
        index = data.get('index')

        if not url or not index:
            return jsonify({'success': False, 'error': 'URL e índice son requeridos'}), 400

        lista_ext_navegar = [ext.strip() for ext in extensiones_navegar.split(',')]
        lista_tipos_archivos = [ext.strip() for ext in tipos_archivos.split(',')]

        todas_extensiones = lista_ext_navegar + lista_tipos_archivos

        scraper = WebScraping(dominio_base=url.rsplit('/', 1)[0] + '/')

        carpeta_upload = 'static/uploads'
        Funciones.crear_carpeta(carpeta_upload)
        Funciones.borrar_contenido_carpeta(carpeta_upload)

        json_path = os.path.join(carpeta_upload, 'links.json')

        resultado = scraper.extraer_todos_los_links(
            url_inicial=url,
            json_file_path=json_path,
            listado_extensiones=todas_extensiones,
            max_iteraciones=50
        )

        if not resultado['success']:
            return jsonify({'success': False, 'error': 'Error al extraer enlaces'}), 500

        resultado_descarga = scraper.descargar_pdfs(json_path, carpeta_upload)

        scraper.close()

        archivos = Funciones.listar_archivos_carpeta(carpeta_upload, lista_tipos_archivos)

        return jsonify({
            'success': True,
            'archivos': archivos,
            'mensaje': f'Se descargaron {len(archivos)} archivos',
            'stats': {
                'total_enlaces': resultado['total_links'],
                'descargados': resultado_descarga.get('descargados', 0),
                'errores': resultado_descarga.get('errores', 0)
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ADMIN ====================

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        flash('Por favor inicia sesión', 'warning')
        return redirect(url_for('login'))

    return render_template('admin.html',
                        usuario=session.get('usuario'),
                        permisos=session.get('permisos'))

# ==================== MAIN ====================

if __name__ == '__main__':
    Funciones.crear_carpeta('static/uploads')

    print("\n" + "="*50)
    print("VERIFICANDO CONEXIONES")

    print("MongoDB Atlas:", "Conectado ✅" if mongo.test_connection() else "Error ❌")
    print("ElasticSearch:", "Conectado ✅" if elastic.test_connection() else "Error ❌")

    app.run(debug=True, host='0.0.0.0', port=5000)
