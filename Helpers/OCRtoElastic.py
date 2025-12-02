import os
import json
from typing import List, Dict
from pdf2image import convert_from_path
import pytesseract
from datetime import datetime
from Helpers import Funciones


class OCRtoElastic:
    """
    Convierte PDFs a JSON usando OCR y los envía a ElasticSearch
    """

    def __init__(self, elastic_instance, index_name="index_normatividad"):
        self.elastic = elastic_instance
        self.index = index_name

    # =========================================
    # PROCESAR TODOS LOS PDFs
    # =========================================
    def procesar_y_enviar(self, carpeta_pdfs: str, carpeta_json: str = "static/uploads/json"):
        Funciones.crear_carpeta(carpeta_json)
        Funciones.borrar_contenido_carpeta(carpeta_json)

        archivos = [f for f in os.listdir(carpeta_pdfs) if f.lower().endswith(".pdf")]

        documentos = []

        for pdf_file in archivos:
            ruta_pdf = os.path.join(carpeta_pdfs, pdf_file)
            print(f"\n Procesando PDF: {pdf_file}")

            data = self._procesar_pdf(ruta_pdf)
            json_path = os.path.join(carpeta_json, pdf_file.replace(".pdf", ".json"))

            # Guardar JSON local
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            documentos.append(data)

        # Enviar a ElasticSearch
        print("\n Enviando documentos a ElasticSearch...")
        resultado = self.elastic.indexar_bulk(self.index, documentos)

        print(" Resultado Elastic:")
        print(resultado)

        return {
            "success": True,
            "json_generados": len(documentos),
            "elastic": resultado
        }

    # =========================================
    # PROCESAR PDF INDIVIDUAL
    # =========================================
    def _procesar_pdf(self, ruta_pdf: str) -> Dict:
        texto_total = ""
        paginas = convert_from_path(ruta_pdf, dpi=150)

        for img in paginas:
            texto_total += pytesseract.image_to_string(img, lang="spa") + "\n"

        documento = {
            "archivo": os.path.basename(ruta_pdf),
            "texto_ocr": texto_total,
            "num_paginas": len(paginas),
            "caracteres": len(texto_total),
            "fecha_procesado": datetime.now().isoformat()
        }

        return documento
