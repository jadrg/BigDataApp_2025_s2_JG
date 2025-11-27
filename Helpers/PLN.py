import spacy
import nltk
from nltk.corpus import stopwords
from collections import Counter
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer
from transformers import pipeline
import pandas as pd
from typing import List, Dict, Tuple
import warnings

warnings.filterwarnings('ignore')

# Descarga silenciosa de recursos NLTK
try:
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)
except Exception:
    pass


class PLN:
    """Procesamiento de Lenguaje Natural en español."""

    def __init__(
        self,
        modelo_spacy: str = 'es_core_news_lg',
        modelo_embeddings: str = 'paraphrase-multilingual-MiniLM-L12-v2',
        cargar_modelos: bool = True
    ):
        self.modelo_spacy_nombre = modelo_spacy
        self.modelo_embeddings_nombre = modelo_embeddings
        self.nlp = None
        self.model_embeddings = None
        self.stopwords_es = None

        if cargar_modelos:
            self._cargar_modelos()

    # ===============================================================
    # CARGAR MODELOS
    # ===============================================================
    def _cargar_modelos(self):
        """Carga spaCy, SentenceTransformer y stopwords."""

        # spaCy
        try:
            self.nlp = spacy.load(self.modelo_spacy_nombre)
        except Exception:
            try:
                self.nlp = spacy.load('es_core_news_sm')
            except Exception:
                self.nlp = None

        # Embeddings
        try:
            self.model_embeddings = SentenceTransformer(self.modelo_embeddings_nombre)
        except Exception:
            self.model_embeddings = None

        # Stopwords
        try:
            self.stopwords_es = set(stopwords.words('spanish'))
        except Exception:
            nltk.download('stopwords', quiet=True)
            self.stopwords_es = set(stopwords.words('spanish'))

    # ===============================================================
    # ENTIDADES
    # ===============================================================
    def extraer_entidades(self, texto: str) -> Dict[str, List[str]]:
        """Extrae entidades nombradas usando spaCy."""

        if not self.nlp:
            raise ValueError("Modelo spaCy no cargado.")

        doc = self.nlp(texto)

        entidades = {
            'personas': [],
            'lugares': [],
            'organizaciones': [],
            'fechas': [],
            'leyes': [],
            'otros': []
        }

        for ent in doc.ents:
            label = ent.label_
            text = ent.text

            if label == 'PER':
                entidades['personas'].append(text)
            elif label == 'LOC':
                entidades['lugares'].append(text)
            elif label == 'ORG':
                entidades['organizaciones'].append(text)
            elif label == 'DATE':
                entidades['fechas'].append(text)
            elif label == 'LAW' or 'ley ' in text.lower():
                entidades['leyes'].append(text)
            else:
                entidades['otros'].append(f"{text} ({label})")

        # eliminar duplicados manteniendo orden
        for key in entidades:
            entidades[key] = list(dict.fromkeys(entidades[key]))

        return entidades

    # ===============================================================
    # TEMAS
    # ===============================================================
    def extraer_temas(self, texto: str, top_n: int = 10) -> List[Tuple[str, float]]:
        """Extrae las palabras clave más relevantes."""

        if not self.nlp:
            raise ValueError("Modelo spaCy no cargado.")

        doc = self.nlp(texto)

        palabras = [
            token.lemma_.lower()
            for token in doc
            if (
                not token.is_stop
                and not token.is_punct
                and len(token.text) > 3
                and token.pos_ in ['NOUN', 'PROPN', 'ADJ', 'VERB']
            )
        ]

        contador = Counter(palabras)
        temas = contador.most_common(top_n)

        total = len(palabras)
        if total > 0:
            temas = [(p, (f / total) * 100) for p, f in temas]
        else:
            temas = [(p, 0.0) for p, f in temas]

        return temas

    # ===============================================================
    # RESUMEN
    # ===============================================================
    def generar_resumen(self, texto: str, num_oraciones: int = 3) -> str:
        """Genera un resumen extractivo con TF-IDF."""

        if not self.nlp:
            raise ValueError("Modelo spaCy no cargado.")

        doc = self.nlp(texto)
        oraciones = [s.text.strip() for s in doc.sents if len(s.text.strip()) > 20]

        if len(oraciones) <= num_oraciones:
            return ' '.join(oraciones)

        try:
            vectorizer = TfidfVectorizer(stop_words=list(self.stopwords_es))
            matriz = vectorizer.fit_transform(oraciones)

            puntajes = np.array(matriz.sum(axis=1)).flatten()
            idx = puntajes.argsort()[-num_oraciones:][::-1]
            idx = sorted(idx)

            return ' '.join(oraciones[i] for i in idx)

        except Exception:
            return ' '.join(oraciones[:num_oraciones])

    # ===============================================================
    # SIMILITUD SEMÁNTICA
    # ===============================================================
    def calcular_similitud_semantica(self, textos: List[str]) -> pd.DataFrame:
        """Calcula similitud entre textos."""

        if not self.model_embeddings:
            raise ValueError("Modelo embeddings no cargado.")

        if len(textos) < 2:
            raise ValueError("Se requieren al menos 2 textos.")

        emb = self.model_embeddings.encode(textos)
        sim = cosine_similarity(emb)

        return pd.DataFrame(
            sim,
            columns=[f"Texto {i+1}" for i in range(len(textos))],
            index=[f"Texto {i+1}" for i in range(len(textos))]
        )

    # ===============================================================
    # PREPROCESAMIENTO
    # ===============================================================
    def preprocesar_texto(
        self,
        texto: str,
        remover_stopwords: bool = True,
        lematizar: bool = True,
        remover_numeros: bool = False,
        min_longitud: int = 3
    ) -> str:

        if not self.nlp:
            raise ValueError("Modelo spaCy no cargado.")

        doc = self.nlp(texto)
        palabras = []

        for token in doc:
            if len(token.text) < min_longitud:
                continue
            if remover_stopwords and token.is_stop:
                continue
            if token.is_punct or token.is_space:
                continue
            if remover_numeros and token.like_num:
                continue

            palabra = token.lemma_.lower() if lematizar else token.text.lower()
            palabras.append(palabra)

        return ' '.join(palabras)

    # ===============================================================
    # SENTIMIENTO
    # ===============================================================
    def analizar_sentimiento(self, texto: str,
                            modelo: str = 'nlptown/bert-base-multilingual-uncased-sentiment') -> Dict:

        try:
            classifier = pipeline("sentiment-analysis", model=modelo, tokenizer=modelo)
            r = classifier(texto)[0]
            return {'sentimiento': r['label'], 'score': r['score']}
        except Exception as e:
            return {'sentimiento': 'ERROR', 'score': 0.0, 'error': str(e)}

    # ===============================================================
    # NOMBRES PROPIOS
    # ===============================================================
    def extraer_nombres_propios(self, texto: str) -> List[str]:
        if not self.nlp:
            raise ValueError("Modelo spaCy no cargado.")

        doc = self.nlp(texto)
        nombres = [t.text for t in doc if t.pos_ == 'PROPN' and len(t.text) > 2]

        return list(dict.fromkeys(nombres))

    # ===============================================================
    # CONTAR PALABRAS
    # ===============================================================
    def contar_palabras(self, texto: str, unicas: bool = False) -> int:
        if not self.nlp:
            raise ValueError("Modelo spaCy no cargado.")

        doc = self.nlp(texto)

        palabras = [
            t.text.lower() for t in doc
            if not t.is_punct and not t.is_space and not t.is_stop
        ]

        return len(set(palabras)) if unicas else len(palabras)

    # ===============================================================
    # CLOSE
    # ===============================================================
    def close(self):
        pass
