import os
import json
import time
from typing import List, Dict

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from Helpers import Funciones


class WebScraping:
    """
    WebScraping con Selenium adaptado a tu proyecto Flask:
    - Usa Selenium (igual que tu .ipynb)
    - Recorre secciones (Leyes, Decretos, etc.)
    - Extrae PDF, DOCX, XLSX
    - Guarda JSON en static/uploads
    """

    # ================================
    # SECCIONES A SCRAPEAR
    # ================================
    SECCIONES = {
        "Leyes": "https://minvivienda.gov.co/normativa?f%5B0%5D=tipo_normativa%3ALey",
        "Decretos": "https://minvivienda.gov.co/normativa?f%5B0%5D=tipo_normativa%3ADecreto",
        "Resoluciones": "https://minvivienda.gov.co/normativa?f%5B0%5D=tipo_normativa%3AResoluci%C3%B3n",
        "Conceptos_Juridicos": "https://minvivienda.gov.co/normativa?f%5B0%5D=tipo_normativa%3AConcepto",
        "Circulares":"https://minvivienda.gov.co/normativa?f%5B0%5D=tipo_normativa%3ACircular#views-exposed-form-normativa-block-1"
        # "Agenda_Regulatoria": "https://minvivienda.gov.co/normativa?f%5B0%5D=tipo_normativa%3AAgenda%20Regulatoria"
    }

    DOMINIO = "https://minvivienda.gov.co"

    def __init__(self, headless: bool = True):
        """
        Inicializa Selenium con opciones compatibles en Windows y Render.
        """
        chrome_options = Options()

        if headless:
            chrome_options.add_argument("--headless=new")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(options=chrome_options)

    # ===============================================================
    # EXTRAER LINKS DE UNA SECCIÓN
    # ===============================================================
    def extraer_links_seccion(self, url_seccion: str) -> List[Dict]:
        """Extrae enlaces de la sección con paginación."""
        links = []

        try:
            self.driver.get(url_seccion)
            time.sleep(2)

            while True:
                html = self.driver.page_source
                soup = BeautifulSoup(html, "lxml")

                elementos = soup.select("div.views-row a")

                for tag in elementos:
                    href = tag.get("href")
                    if not href:
                        continue

                    # Si el href YA es una URL completa → NO concatenar dominio
                    if href.startswith("http"):
                        url_completa = href
                    else:
                        url_completa = f"{self.DOMINIO}{href}"

                    # Guardar solo documentos útiles
                    if url_completa.lower().endswith((".pdf", ".docx", ".xlsx")):
                        extension = url_completa.split(".")[-1].lower()
                        links.append({
                            "url": url_completa,
                            "type": extension
                        })

                # Buscar el botón de siguiente página
                boton = soup.select_one("li.pager__item--next a")
                if boton:
                    next_href = boton.get("href")

                    if next_href.startswith("http"):
                        siguiente = next_href
                    else:
                        siguiente = f"{self.DOMINIO}{next_href}"

                    self.driver.get(siguiente)
                    time.sleep(2)
                else:
                    break

        except Exception as e:
            print(f"Error en la sección {url_seccion}: {e}")

        return links

    # ===============================================================
    # RECORRER TODAS LAS SECCIONES Y GUARDAR JSON
    # ===============================================================
    def extraer_todos_los_links(self, json_destino: str) -> Dict:
        """
        Recorre todas las secciones y guarda los links en un JSON.
        """
        carpeta = os.path.dirname(json_destino)
        Funciones.crear_carpeta(carpeta)
        Funciones.borrar_contenido_carpeta(carpeta)

        todos = []

        for nombre, url_seccion in self.SECCIONES.items():
            print(f"\n=== Scraping sección: {nombre} ===")
            lista = self.extraer_links_seccion(url_seccion)

            for l in lista:
                l["seccion"] = nombre

            todos.extend(lista)

        # Guardar JSON
        self._guardar_links(json_destino, todos)

        return {
            "success": True,
            "total_links": len(todos),
            "links": todos
        }

    # ===============================================================
    # DESCARGAR PDFs USANDO REQUESTS
    # ===============================================================
    def descargar_pdfs(self, json_path: str, carpeta_destino: str = "static/uploads") -> Dict:

        links = self._cargar_links(json_path)
        pdfs = [l for l in links if l["type"] == "pdf"]

        Funciones.crear_carpeta(carpeta_destino)
        Funciones.borrar_contenido_carpeta(carpeta_destino)

        import requests

        descargados = 0
        errores = []

        for link in pdfs:
            url = link["url"]
            nombre = os.path.basename(url)
            destino = os.path.join(carpeta_destino, nombre)

            try:
                res = requests.get(url, timeout=30)
                res.raise_for_status()

                with open(destino, "wb") as f:
                    f.write(res.content)

                descargados += 1

            except Exception as e:
                errores.append({"url": url, "error": str(e)})

        return {
            "success": True,
            "total": len(pdfs),
            "descargados": descargados,
            "errores": errores
        }

    # ===============================================================
    # JSON HELPERS
    # ===============================================================
    def _guardar_links(self, path: str, lista_links: List[Dict]):
        """Guardar JSON con formato estándar de tu App."""
        data = {"links": lista_links}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _cargar_links(self, path: str) -> List[Dict]:
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("links", [])

    # ===============================================================
    # CERRAR SELENIUM
    # ===============================================================
    def close(self):
        """Cerrar Selenium correctamente."""
        try:
            self.driver.quit()
        except:
            pass