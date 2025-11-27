import os
import zipfile
import requests
import json
import PyPDF2
from PIL import Image
import pytesseract
from typing import Dict, List
from werkzeug.utils import secure_filename
from datetime import datetime


class Funciones:

    @staticmethod
    def crear_carpeta(ruta: str) -> bool:
        """Crea una carpeta si no existe."""
        try:
            if not os.path.exists(ruta):
                os.makedirs(ruta)
            return True
        except Exception as e:
            print(f"Error al crear carpeta: {e}")
            return False

    @staticmethod
    def descomprimir_zip_local(ruta_file_zip: str, ruta_descomprimir: str) -> List[Dict]:
        """Descomprime un ZIP local y retorna información de archivos extraídos."""
        archivos = []
        try:
            with zipfile.ZipFile(ruta_file_zip, 'r') as zip_ref:
                for file_info in zip_ref.namelist():
                    if file_info.endswith('/'):
                        continue

                    carpeta = os.path.dirname(file_info)
                    nombre_archivo = os.path.basename(file_info)
                    extension = os.path.splitext(nombre_archivo)[1].lower()

                    if extension in ['.txt', '.pdf', '.json']:
                        zip_ref.extract(file_info, ruta_descomprimir)
                        archivos.append({
                            'carpeta': carpeta or 'raiz',
                            'nombre': nombre_archivo,
                            'ruta': os.path.join(ruta_descomprimir, file_info),
                            'extension': extension
                        })

            return archivos
        except Exception as e:
            print(f"Error al descomprimir ZIP: {e}")
            return []

    @staticmethod
    def descargar_y_descomprimir_zip(url: str, carpeta_destino: str, tipoArchivo: str = '') -> List[Dict]:
        """Descarga un ZIP desde URL y lo descomprime."""
        try:
            Funciones.crear_carpeta(carpeta_destino)

            response = requests.get(url, stream=True)
            zip_path = os.path.join(carpeta_destino, 'temp.zip')

            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            archivos = Funciones.descomprimir_zip_local(zip_path, carpeta_destino)

            os.remove(zip_path)

            return archivos

        except Exception as e:
            print(f"Error al descargar/descomprimir ZIP: {e}")
            return []

    @staticmethod
    def allowed_file(filename: str, extensions: List[str]) -> bool:
        """Valida si un archivo tiene extensión permitida."""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions

    @staticmethod
    def borrar_contenido_carpeta(ruta: str) -> bool:
        """Borra todo el contenido de una carpeta sin eliminarla."""
        try:
            if not os.path.exists(ruta):
                return True

            if not os.path.isdir(ruta):
                return False

            for item in os.listdir(ruta):
                item_path = os.path.join(ruta, item)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        import shutil
                        shutil.rmtree(item_path)
                except Exception as e:
                    print(f"Error al eliminar {item_path}: {e}")
                    return False

            return True

        except Exception as e:
            print(f"Error al borrar contenido: {e}")
            return False

    @staticmethod
    def extraer_texto_pdf(ruta_pdf: str) -> str:
        """Extrae texto de un PDF (no escaneado)."""
        try:
            texto = ""
            with open(ruta_pdf, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    texto += (page.extract_text() or "") + "\n"
            return texto.strip()
        except Exception as e:
            print(f"Error al extraer texto PDF {ruta_pdf}: {e}")
            return ""

    @staticmethod
    def extraer_texto_pdf_ocr(ruta_pdf: str) -> str:
        """Extrae texto de un PDF escaneado mediante OCR."""
        try:
            from pdf2image import convert_from_path

            images = convert_from_path(ruta_pdf)
            texto = ""

            for image in images:
                texto += pytesseract.image_to_string(image, lang='spa') + "\n"

            return texto.strip()

        except Exception as e:
            print(f"Error OCR en PDF {ruta_pdf}: {e}")
            return ""

    @staticmethod
    def listar_archivos_json(ruta_carpeta: str) -> List[Dict]:
        """Lista archivos JSON en un directorio."""
        try:
            if not os.path.exists(ruta_carpeta):
                return []

            archivos = []
            for archivo in os.listdir(ruta_carpeta):
                if archivo.lower().endswith('.json'):
                    ruta = os.path.join(ruta_carpeta, archivo)
                    archivos.append({
                        'nombre': archivo,
                        'ruta': ruta,
                        'tamaño': os.path.getsize(ruta)
                    })

            return archivos

        except Exception as e:
            print(f"Error listando JSON: {e}")
            return []

    @staticmethod
    def listar_archivos_carpeta(ruta_carpeta: str, extensiones: List[str] = None) -> List[Dict]:
        """Lista archivos del directorio filtrados por extensión."""
        try:
            if not os.path.exists(ruta_carpeta):
                return []

            archivos = []

            for archivo in os.listdir(ruta_carpeta):
                ruta = os.path.join(ruta_carpeta, archivo)
                if os.path.isfile(ruta):

                    extension = os.path.splitext(archivo)[1].lower().replace('.', '')

                    if extensiones is None or extension in extensiones:
                        archivos.append({
                            'nombre': archivo,
                            'ruta': ruta,
                            'extension': extension,
                            'tamaño': os.path.getsize(ruta)
                        })

            return archivos

        except Exception as e:
            print(f"Error listando archivos: {e}")
            return []

    @staticmethod
    def leer_json(ruta_json: str) -> Dict:
        """Lee un archivo JSON desde disco."""
        try:
            with open(ruta_json, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error al leer JSON {ruta_json}: {e}")
            return {}

    @staticmethod
    def guardar_json(ruta_json: str, datos: Dict) -> bool:
        """Guarda datos en un archivo JSON."""
        try:
            directorio = os.path.dirname(ruta_json)
            if directorio:
                Funciones.crear_carpeta(directorio)

            with open(ruta_json, 'w', encoding='utf-8') as f:
                json.dump(datos, f, indent=4, ensure_ascii=False)
            return True

        except Exception as e:
            print(f"Error al guardar JSON: {e}")
            return False
