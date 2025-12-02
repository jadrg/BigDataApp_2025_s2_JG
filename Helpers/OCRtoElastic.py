# Helpers/OCRtoElastic.py

import os
import json
from typing import Dict, List
import pdfplumber
from datetime import datetime
from Helpers import Funciones


class OCRtoElastic:
    """
    Extrae texto de PDFs (si tienen texto embebido), genera JSON
    y luego envía esos JSON a ElasticSearch.
    """

    def __init__(self, elastic_instance, index_name: str = "index_normatividad"):
        self.elastic = elastic_instance
        self.index = index_name

    # ============================================================
    # MÉTODO PÚBLICO: PROCESAR TODOS LOS PDFs Y ENVIAR A ELASTIC
    # ============================================================
    def procesar_y_enviar(self, carpeta_pdfs: str,
                        carpeta_json: str = "static/uploads/json") -> Dict:
        """
        1. Lee todos los PDFs de `carpeta_pdfs`.
        2. Genera un JSON por PDF en `carpeta_json`.
        3. Carga todos los JSON generados.
        4. Envía los JSON a ElasticSearch con indexar_bulk.
        """

        # Asegurar carpeta para JSON
        Funciones.crear_carpeta(carpeta_json)
        Funciones.borrar_contenido_carpeta(carpeta_json)

        # Buscar PDFs
        pdf_files = [
            f for f in os.listdir(carpeta_pdfs)
            if f.lower().endswith(".pdf")
        ]

        json_paths: List[str] = []
        errores_pdf: List[Dict] = []

        for pdf_file in pdf_files:
            ruta_pdf = os.path.join(carpeta_pdfs, pdf_file)
            print(f"Procesando PDF: {pdf_file}")

            data = self._procesar_pdf(ruta_pdf)

            # Guardar JSON local
            nombre_json = os.path.splitext(pdf_file)[0] + ".json"
            json_path = os.path.join(carpeta_json, nombre_json)

            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                json_paths.append(json_path)
            except Exception as e:
                errores_pdf.append({
                    "archivo": pdf_file,
                    "error": f"Error guardando JSON: {e}"
                })

        # ====================================================
        #  Cargar SOLO los JSON y enviarlos a ElasticSearch
        # ====================================================
        documentos: List[Dict] = []
        errores_json: List[Dict] = []

        for path in json_paths:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    documentos.append(json.load(f))
            except Exception as e:
                errores_json.append({
                    "archivo_json": os.path.basename(path),
                    "error": f"Error leyendo JSON: {e}"
                })

        if documentos:
            resultado_elastic = self.elastic.indexar_bulk(self.index, documentos)
        else:
            resultado_elastic = {
                "success": False,
                "error": "No hay documentos JSON para indexar en ElasticSearch"
            }

        return {
            "success": True,
            "total_pdfs": len(pdf_files),
            "json_generados": len(json_paths),
            "documentos_enviados_elastic": len(documentos),
            "errores_pdf": errores_pdf,
            "errores_json": errores_json,
            "resultado_elastic": resultado_elastic
        }

    # ============================================================
    # MÉTODO PRIVADO: PROCESAR UN PDF INDIVIDUAL
    # ============================================================
    def _procesar_pdf(self, ruta_pdf: str) -> Dict:
        """
        Extrae texto de un solo PDF usando pdfplumber.
        Si el PDF no tiene texto embebido, se marca con tiene_texto = False.
        """

        texto_paginas: List[str] = []
        num_paginas = 0

        try:
            with pdfplumber.open(ruta_pdf) as pdf:
                num_paginas = len(pdf.pages)

                for pagina in pdf.pages:
                    texto = pagina.extract_text() or ""
                    texto_paginas.append(texto)

        except Exception as e:
            # Error al abrir o leer el PDF
            return {
                "archivo": os.path.basename(ruta_pdf),
                "texto_ocr": "",
                "num_paginas": num_paginas,
                "caracteres": 0,
                "tiene_texto": False,
                "motivo_sin_texto": f"Error extrayendo texto: {e}",
                "fecha_procesado": datetime.now().strftime("%Y-%m-%d")
            }

        # Unir texto de todas las páginas
        texto_total = "\n\n".join(texto_paginas)

        # Limpiar un poco para contar caracteres de forma más real
        texto_limpio = texto_total.replace("\u0000", "").strip()
        num_caracteres = len(texto_limpio)

        # Umbral mínimo para considerar que realmente tiene texto
        umbral_minimo = 20
        tiene_texto = num_caracteres >= umbral_minimo

        documento: Dict = {
            "archivo": os.path.basename(ruta_pdf),
            "texto_ocr": texto_total,
            "num_paginas": num_paginas,
            "caracteres": num_caracteres,
            "tiene_texto": tiene_texto,
            "fecha_procesado": datetime.now().strftime("%Y-%m-%d")
        }

        if not tiene_texto:
            documento["motivo_sin_texto"] = "PDF sin texto embebido (probable escaneo)"

        return documento