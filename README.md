Proyecto de BIG DATA – Maestría en Analítica de Datos
Aplicación MinVikVivienda
Repositorio académico y técnico del proyecto de Big Data desarrollado como parte de la Maestría en Analítica de Datos.

Autor
Jader A. Gómez
Correo: jgomezo@ucentral.edu.co

Descripción del Proyecto
Este repositorio contiene el desarrollo completo del proyecto MinVikVivienda, una aplicación orientada a la ingestión, procesamiento, análisis y visualización de datos relacionados con información normativa, técnica y documental asociada al Ministerio de Vivienda.

El proyecto combina Web Scraping, ETL, Machine Learning, Almacenamiento NoSQL y servicios de búsqueda inteligentes, integrando herramientas como:

Python + Flask

MongoDB Atlas

ElasticSearch

Web Scraping (PDFs y HTML)

Dashboards y análisis exploratorio

Automatización y pipelines de datos

El objetivo principal es construir un ecosistema Big Data funcional, capaz de recolectar documentos, indexarlos, analizarlos y facilitar su consulta eficiente.

Características Principales
✔ Extracción automatizada de PDFs y páginas web
✔ Limpieza, procesamiento y estructuración de datos
✔ API desarrollada en Flask
✔ Integración con ElasticSearch para búsquedas avanzadas
✔ Almacenamiento en MongoDB
✔ Scripts modulares en la carpeta Helpers
✔ Arquitectura escalable tipo Big Data

Estructura del Repositorio (sugerida)

/
├── app.py
├── requirements.txt
├── .env.template
├── Helpers/
│ ├── MongoDB.py
│ ├── ElasticSearch.py
│ ├── Funciones.py
│ └── WebScraping.py
├── data/
│ ├── raw/
│ ├── processed/
│ └── pdfs/
└── README.md

Tecnologías Utilizadas
Python 3.10+ – Backend, scraping y ETL
Flask – Aplicación web
MongoDB Atlas – Base de datos NoSQL
ElasticSearch Cloud – Motor de búsqueda
BeautifulSoup / Requests – Scraping
Pandas / NumPy – Transformación de datos
GitHub – Control de versiones