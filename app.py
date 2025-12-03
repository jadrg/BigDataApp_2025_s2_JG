from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from dotenv import load_dotenv
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from Helpers import MongoDB, ElasticSearch, Funciones, WebScraping, OCRtoElastic, PLN

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
    index_name=ELASTIC_INDEX_DEFAULT
)

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
        # Campo donde guardamos el texto del OCR
        campo = 'texto_ocr'

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
    # CORREGIDO: antes 'admin_Usuarios'
    if not permisos.get('admin_usuarios'):
        flash('No tiene permisos para gestionar usuarios', 'danger')
        return redirect(url_for('admin'))

    return render_template(
        'gestor_usuarios.html',
        usuario=session.get('usuario'),
        permisos=permisos,
        version=VERSION_APP,
        creador=CREATOR_APP
    )

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

        if resultado:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'success': False, 'error': 'Error al crear usuario'}), 500

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

        if resultado:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'success': False, 'error': 'Error al actualizar usuario'}), 500

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

        if resultado:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'success': False, 'error': 'Error al eliminar usuario'}), 500

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

    return render_template(
        'documentos_elastic.html',
        usuario=session.get('usuario'),
        permisos=permisos,
        version=VERSION_APP,
        creador=CREATOR_APP
    )

# ----------- Web Scraping para Elastic -----------

@app.route('/procesar-webscraping-elastic', methods=['POST'])
def procesar_webscraping_elastic():
    """
    - Extrae únicamente los PDFs.
    - Descarga los PDFs en static/uploads.
    - Devuelve la lista de PDFs al frontend.
    NO hace OCR, NO indexa en Elastic.
    """
    try:
        # ---------- 1. Validar sesión y permisos ----------
        if not session.get('logged_in'):
            return jsonify({'success': False, 'error': 'No autorizado'}), 401

        permisos = session.get('permisos', {})
        if not permisos.get('admin_data_elastic'):
            return jsonify({'success': False, 'error': 'No tiene permisos'}), 403

        # ---------- 2. Preparar carpetas de trabajo ----------
        carpeta_pdfs = os.path.join('static', 'uploads')
        json_links_path = os.path.join(carpeta_pdfs, 'links_minvivienda.json')

        Funciones.crear_carpeta(carpeta_pdfs)
        Funciones.borrar_contenido_carpeta(carpeta_pdfs)

        # ---------- 3. Scrapin ----------
        print("\n=== [SCRAPING] Extrayendo enlaces de Minvivienda ===")

        scraper = WebScraping(headless=True)

        resultado_links = scraper.extraer_todos_los_links(
            json_destino=json_links_path
        )

        print(f"Links encontrados: {resultado_links.get('total_links',0)}")

        # ---------- 4. Descargar SOLO PDFs ----------
        print("\n=== [DESCARGA] Descargando PDFs ===")

        resultado_descarga = scraper.descargar_pdfs(
            json_path=json_links_path,
            carpeta_destino=carpeta_pdfs
        )

        scraper.close()

        # ---------- 5. Listar los PDFs descargados ----------
        archivos = Funciones.listar_archivos_carpeta(carpeta_pdfs, ['pdf'])

        return jsonify({
            'success': True,
            'archivos': archivos,
            'mensaje': f"{len(archivos)} PDFs descargados correctamente.",
            'stats': {
                'total_links': resultado_links.get('total_links', 0),
                'descargados': resultado_descarga.get('descargados', 0),
                'errores': len(resultado_descarga.get('errores', []))
            }
        })

    except Exception as e:
        print("Error en procesar_webscraping_elastic:", e)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/cargar-documentos-elastic', methods=['POST'])
def cargar_documentos_elastic():
    """API para cargar documentos a ElasticSearch"""
    try:
        # ---------------- VALIDACIÓN DE SESIÓN ----------------
        if not session.get('logged_in'):
            return jsonify({'success': False, 'error': 'No autorizado'}), 401

        permisos = session.get('permisos', {})
        if not permisos.get('admin_data_elastic'):
            return jsonify({'success': False, 'error': 'No tiene permisos para cargar datos'}), 403

        # ---------------- LEER DATOS DEL REQUEST ----------------
        data = request.get_json()
        archivos = data.get('archivos', [])
        index = data.get('index')
        metodo = data.get('metodo', 'zip')

        if not archivos or not index:
            return jsonify({'success': False, 'error': 'Archivos e índice son requeridos'}), 400

        documentos = []

        # ===========================================================
        # MÉTODO 1: ZIP — CARGAR JSON DIRECTAMENTE
        # ===========================================================
        if metodo == 'zip':
            for archivo in archivos:
                ruta = archivo.get('ruta')

                if ruta and os.path.exists(ruta):
                    doc = Funciones.leer_json(ruta)
                    if doc:
                        documentos.append(doc)

        # ===========================================================
        # MÉTODO 2: WEBSCRAPING — PROCESAR ARCHIVOS UNO POR UNO
        # ===========================================================
        elif metodo == 'webscraping':
            # Procesar archivos con PLN
            pln = PLN(cargar_modelos=True)

            for archivo in archivos:
                ruta = archivo.get('ruta')
                if not ruta or not os.path.exists(ruta):
                    continue

                extension = archivo.get('extension', '').lower()

                # Extraer texto según tipo de archivo
                texto = ""
                
                if extension == 'pdf':
                    # Intentar extracción normal
                    texto = Funciones.extraer_texto_pdf(ruta)

                    # Si no se extrajo texto, intentar con OCR
                    if not texto or len(texto.strip()) < 100:
                        try:
                            texto = Funciones.extraer_texto_pdf_ocr(ruta)
                        except:
                            pass

                elif extension == 'txt':
                    try:
                        with open(ruta, 'r', encoding='utf-8') as f:
                            texto = f.read()
                    except:
                        try:
                            with open(ruta, 'r', encoding='latin-1') as f:
                                texto = f.read()
                        except:
                            pass

                if not texto or len(texto.strip()) < 50:
                    continue

                # Procesar con PLN
                try:
                    # resumen = pln.generar_resumen(texto, num_oraciones=3)
                    # entidades = pln.extraer_entidades(texto)
                    # temas = pln.extraer_temas(texto, top_n=10)

                    resumen = ""      # borrar en producción
                    entidades = ""    # borrar en producción
                    temas = ""        # borrar en producción

                    # Crear documento
                    documento = {
                        'texto': texto,
                        'fecha': datetime.now().isoformat(),
                        'ruta': ruta,
                        'nombre_archivo': archivo.get('nombre', ''),
                        'resumen': resumen,
                        'entidades': entidades,
                        'temas': [{'palabra': palabra, 'relevancia': relevancia} for palabra, relevancia in temas]
                    }

                    documentos.append(documento)

                except Exception as e:
                    print(f"Error al procesar {archivo.get('nombre')}: {e}")
                    continue

            # pln.close()

        if not documentos:
            return jsonify({'success': False, 'error': 'No se pudieron procesar documentos'}), 400

        # Indexar documentos en Elastic
        resultado = elastic.indexar_bulk(index, documentos)

        return jsonify({
            'success': resultado['success'],
            'indexados': resultado['indexados'],
            'errores': resultado['fallidos']
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/procesar-zip-elastic', methods=['POST'])
def procesar_zip_elastic():
    """API para procesar archivo ZIP con archivos JSON"""
    try:
        if not session.get('logged_in'):
            return jsonify({'success': False, 'error': 'No autorizado'}), 401

        permisos = session.get('permisos', {})
        if not permisos.get('admin_data_elastic'):
            return jsonify({'success': False, 'error': 'No tiene permisos para cargar datos'}), 403

        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No se envió ningún archivo'}), 400

        file = request.files['file']
        index = request.form.get('index')

        if not file.filename:
            return jsonify({'success': False, 'error': 'Archivo no válido'}), 400

        if not index:
            return jsonify({'success': False, 'error': 'Índice no especificado'}), 400

        # Guardar archivo ZIP temporalmente
        filename = secure_filename(file.filename)
        carpeta_upload = 'static/uploads'
        Funciones.crear_carpeta(carpeta_upload)
        Funciones.borrar_contenido_carpeta(carpeta_upload)

        zip_path = os.path.join(carpeta_upload, filename)
        file.save(zip_path)

        # Descomprimir ZIP
        archivos = Funciones.descomprimir_zip_local(zip_path, carpeta_upload)

        # Eliminar archivo ZIP
        os.remove(zip_path)

        # Listar archivos JSON
        archivos_json = Funciones.listar_archivos_json(carpeta_upload)

        return jsonify({
            'success': True,
            'archivos': archivos_json,
            'mensaje': f'Se encontraron {len(archivos_json)} archivos JSON'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



# ==================== ADMIN ====================

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        flash('Por favor inicia sesión', 'warning')
        return redirect(url_for('login'))

    return render_template(
        'admin.html',
        usuario=session.get('usuario'),
        permisos=session.get('permisos')
    )

# ==================== MAIN ====================

if __name__ == '__main__':
    Funciones.crear_carpeta('static/uploads')

    print("\n" + "=" * 50)
    print("VERIFICANDO CONEXIONES")
    print("MongoDB Atlas:", "Conectado ✅" if mongo.test_connection() else "Error ❌")
    print("ElasticSearch:", "Conectado ✅" if elastic.test_connection() else "Error ❌")

    app.run(debug=True, host='0.0.0.0', port=5000)