from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from dotenv import load_dotenv
import os
from datetime import datetime

# Helpers correctos
from Helpers.mongoDB import MongoDB
from Helpers.elastic import ElasticSearch
from Helpers.funciones import Funciones
from Helpers.webScraping import WebScraping
from Helpers.OCRtoElastic import OCRtoElastic   # Clase correcta

# ==================== CONFIGURACIÓN ====================
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_super_secreta_12345')

# MongoDB
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB')
MONGO_COLECCION = os.getenv('MONGO_COLECCION', 'usuario_roles')

# ElasticSearch
ELASTIC_CLOUD_URL = os.getenv('ELASTIC_CLOUD_URL')
ELASTIC_API_KEY = os.getenv('ELASTIC_API_KEY')
ELASTIC_INDEX_DEFAULT = "index_normatividad"

# Metadatos
VERSION_APP = "1.2.0"
CREATOR_APP = "JaderAGO"

# Conexiones
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

# ==================== BUSCADOR ====================
@app.route('/buscador')
def buscador():
    return render_template('buscador.html', version=VERSION_APP, creador=CREATOR_APP)


@app.route('/buscar-elastic', methods=['POST'])
def buscar_elastic():
    try:
        data = request.get_json()
        texto = data.get("texto", "").strip()

        if not texto:
            return jsonify({"success": False, "error": "Texto requerido"}), 400

        query = {
            "query": {
                "match": {
                    "texto_ocr": texto     # campo correcto del OCR
                }
            }
        }

        resultado = elastic.buscar(
            index=ELASTIC_INDEX_DEFAULT,
            query=query,
            size=30
        )

        return jsonify(resultado)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== PROCESO WEB SCRAPING → OCR → ELASTIC ====================

@app.route('/procesar-webscraping-elastic', methods=['POST'])
def procesar_webscraping_elastic():
    try:
        data = request.get_json()
        url = data.get("url")

        if not url:
            return jsonify({"success": False, "error": "URL requerida"}), 400

        carpeta_pdfs = "static/uploads"
        Funciones.crear_carpeta(carpeta_pdfs)
        Funciones.borrar_contenido_carpeta(carpeta_pdfs)

        # SCRAPING
        scraper = WebScraping(dominio_base=url.rsplit('/', 1)[0] + '/')
        json_links = os.path.join(carpeta_pdfs, "links.json")

        resultado = scraper.extraer_todos_los_links(
            url=url,
            json_destino=json_links,
            extensiones=['pdf'],
            profundidad=30
        )

        scraper.descargar_pdfs(json_links, carpeta_pdfs)
        scraper.close()

        # OCR → JSON → ELASTIC
        resultado_ocr = ocr.procesar_carpeta(carpeta_pdfs)

        return jsonify({
            "success": True,
            "links": resultado,
            "ocr": resultado_ocr
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== ADMIN ====================
@app.route('/admin')
def admin():
    if not session.get("logged_in"):
        flash("Inicia sesión", "warning")
        return redirect(url_for("login"))

    return render_template(
        "admin.html",
        usuario=session.get("usuario"),
        permisos=session.get("permisos")
    )


# ================= MAIN ====================
if __name__ == "__main__":
    Funciones.crear_carpeta("static/uploads")

    print("\n===== VERIFICANDO CONEXIONES =====\n")
    print("MongoDB:", "OK" if mongo.test_connection() else "ERROR")
    print("ElasticSearch:", "OK" if elastic.test_connection() else "ERROR")

    app.run(debug=True, host="0.0.0.0", port=5000)
