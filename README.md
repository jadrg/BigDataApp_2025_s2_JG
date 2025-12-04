Proyecto de BIG DATA – Maestría en Analítica de Datos
Aplicación MinVivienda

Repositorio académico y técnico del proyecto desarrollado como parte de la Maestría en Analítica de Datos.
La aplicación MinVivienda constituye una solución Big Data enfocada en la recolección, procesamiento, indexación y análisis de información normativa y documental relacionada con el Ministerio de Vivienda.

Autor

Jader A. Gómez
📧 jgomezo@ucentral.edu.co

Descripción del Proyecto

Este proyecto desarrolla una arquitectura Big Data mediante:

Web Scraping avanzado de sitios y documentos públicos

Descarga y procesamiento automático de archivos PDF

Normalización y transformación de datos

Indexación y consultas inteligentes con ElasticSearch

Almacenamiento NoSQL en MongoDB

Exposición de funcionalidades a través de una API construida en Flask

El propósito es construir un ecosistema capaz de centralizar documentos, analizarlos y ofrecer búsquedas rápidas y eficientes.

Características Principales

Extracción automatizada de PDFs y contenido web

Limpieza, procesamiento y estructuración de datos

API desarrollada en Flask

Integración con ElasticSearch para búsquedas avanzadas

Almacenamiento flexible en MongoDB

Scripts modulares en la carpeta Helpers/

Arquitectura escalable orientada a análisis y automatización

Estructura del Repositorio

/
│── app.py
│── requirements.txt
│── .env.template
│
├── Helpers/
│   ├── MongoDB.py
│   ├── ElasticSearch.py
│   ├── Funciones.py
│   └── WebScraping.py
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── pdfs/
│
└── README.md

Tecnologías Utilizadas

Python 3.10+ – Backend, ETL, scraping
Flask – API y aplicación web
MongoDB Atlas – Base de datos NoSQL
ElasticSearch Cloud – Motor de búsqueda
Requests / BeautifulSoup – Web Scraping
Pandas / NumPy – Transformación de datos
GitHub – Control de versiones