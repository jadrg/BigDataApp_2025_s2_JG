from dotenv import load_dotenv
import os

from Helpers.elastic import ElasticSearch
from Helpers.OCRtoElastic import OCRtoElastic

# Cargar .env
load_dotenv()

CARPETA_PDFS = "static/uploads"
CARPETA_JSON = "static/uploads/json"
INDEX = "index_normatividad"

elastic = ElasticSearch(
    os.getenv("ELASTIC_CLOUD_URL"),
    os.getenv("ELASTIC_API_KEY")
)

ocr = OCRtoElastic(
    elastic_instance=elastic,
    index_name=INDEX
)

if __name__ == "__main__":
    print("\n=== INICIANDO PROCESO EXTRACCIÓN PDF → JSON → ELASTIC ===\n")
    resultado = ocr.procesar_y_enviar(CARPETA_PDFS, CARPETA_JSON)
    print("\n=== FINALIZADO ===")
    print(resultado)