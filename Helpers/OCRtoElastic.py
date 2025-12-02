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
        self.elastic = elastic_instance     # Instancia real
        self.index = index_name             # Índice destino

    # =========================================
    # MÉTODO PÚBLICO PARA PROCESAR 1 PDF
    # =========================================
    def procesar_pdf(self, ruta_pdf: str) -> Dict:
        """
        Procesa un PDF → OCR → JSON → lo envía a ElasticSearch.
        Este SÍ es el método usado en app.py
        """
        data = self._procesar_pdf(ruta_pdf)

        # Guardar el JSON local junto al PDF
        carpeta_json = os.path.join(os.path.dirname(ruta_pdf), "json")
        Funciones.crear_carpeta(carpeta_json)

        json_path = os.path.join(
            carpeta_json,
            os.path.basename(ruta_pdf).replace(".pdf", ".json")
        )

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        # Enviar a ElasticSearch
        try:
            self.elastic.indexar_documento(self.index, data)
        except Exception as e:
            print(f"⚠ Error enviando a Elastic: {e}")

        return data

    # =========================================
    # PROCESAR TODOS LOS PDFs DE UNA CARPETA
    # =========================================
    def procesar_y_enviar(self, carpeta_pdfs: str, carpeta_json: str = "static/uploads/json"):
        Funciones.crear_carpeta(carpeta_json)
        Funciones.borrar_contenido_carpeta(carpeta_json)

        archivos = [f for f in os.listdir(carpeta_pdfs) if f.lower().endswith(".pdf")]
        documentos = []

        for pdf_file in archivos:
            ruta_pdf = os.path.join(carpeta_pdfs, pdf_file)
            print(f"\n📄 Procesando PDF: {pdf_file}")

            data = self._procesar_pdf(ruta_pdf)

            # Guardar JSON local
            json_path = os.path.join(carpeta_json, pdf_file.replace(".pdf", ".json"))
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            documentos.append(data)

        # Enviar en bulk a ElasticSearch
        print("\n🚀 Enviando documentos a ElasticSearch...")
        resultado = self.elastic.indexar_bulk(self.index, documentos)

        return {
            "success": True,
            "json_generados": len(documentos),
            "elastic": resultado
        }

    # =========================================
    # PROCESAR 1 PDF (INTERNO)
    # =========================================
    def _procesar_pdf(self, ruta_pdf: str) -> Dict:
        """
        Extrae OCR del PDF completo.
        """
        texto_total = ""

        try:
            paginas = convert_from_path(ruta_pdf, dpi=150)
        except Exception as e:
            return {
                "archivo": os.path.basename(ruta_pdf),
                "error": f"No se pudo convertir a imágenes: {e}"
            }

        for img in paginas:
            try:
                texto_total += pytesseract.image_to_string(img, lang="spa") + "\n"
            except Exception as e:
                texto_total += f"[ERROR OCR: {e}]"

        return {
            "archivo": os.path.basename(ruta_pdf),
            "texto_ocr": texto_total,
            "num_paginas": len(paginas),
            "caracteres": len(texto_total),
            "fecha_procesado": datetime.now().isoformat()
        }