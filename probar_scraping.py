from Helpers.webScraping import WebScraping
from Helpers.funciones import Funciones
import os


def main():
    print("\n==============================")
    print("   PRUEBA DE WEB SCRAPING SELENIUM")
    print("==============================\n")

    # Carpeta donde guardas todo
    carpeta_destino = "static/uploads"
    Funciones.crear_carpeta(carpeta_destino)

    # Archivo JSON donde se almacenarán los resultados
    json_path = os.path.join(carpeta_destino, "links.json")

    # Crear instancia de tu clase Selenium
    scraper = WebScraping(headless=False)   # True si no quieres ver el navegador

    print("🔎 Extrayendo enlaces de TODAS las secciones...\n")
    resultado_links = scraper.extraer_todos_los_links(json_destino=json_path)

    print("➡️ Resultado extracción:")
    print(resultado_links)

    print("\n📥 Descargando PDFs...\n")
    resultado_descarga = scraper.descargar_pdfs(
        json_path,
        carpeta_destino=carpeta_destino
    )

    print("➡️ Resultado descarga:")
    print(resultado_descarga)

    scraper.close()

    print("\n==============================")
    print("   PROCESO COMPLETADO ✔")
    print("==============================\n")


if __name__ == "__main__":
    main()