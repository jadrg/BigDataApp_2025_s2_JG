from Helpers.OCRtoElastic import OCRtoElastic
from Helpers.elastic import ElasticSearch
import os
from dotenv import load_dotenv

# Cargar variables del .env
load_dotenv()

# Carpeta donde están tus PDFs descargados
CARPETA_PDFS = "static/uploads"

# Carpeta donde se guardarán los JSON
CARPETA_JSON = "static/uploads/json"

# Nombre del índice en Elastic
INDEX = "index_normatividad"

# Instanciar ElasticSearch
elastic = ElasticSearch(
    os.getenv("ELASTIC_CLOUD_URL"),
    os.getenv("ELASTIC_API_KEY")
)

# Instanciar OCR (CLASE CORRECTA)
ocr = OCRtoElastic(
    elastic_instance=elastic,
    index_name=INDEX
)

# Ejecutar OCR → JSON → Elastic
if __name__ == "__main__":
    print("\n=== INICIANDO PROCESO OCR ===\n")
    resultado = ocr.procesar_y_enviar(CARPETA_PDFS, CARPETA_JSON)
    print("\n=== FINALIZADO ===")
    print(resultado)
    print(f"\nDocumentos procesados y enviados a Elastic en el índice '{INDEX}'.")