from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from typing import Dict, List, Optional
import json


class ElasticSearch:
    """Clase para gestionar conexión y operaciones con ElasticSearch Cloud."""

    def __init__(self, cloud_url: str, api_key: str):
        self.client = Elasticsearch(
            cloud_url,
            api_key=api_key,
            verify_certs=True
        )

    # ---------------------------------------------------------
    # CONEXIÓN
    # ---------------------------------------------------------
    def test_connection(self) -> bool:
        try:
            info = self.client.info()
            print(f"✅ Conectado a Elastic: {info['version']['number']}")
            return True
        except Exception as e:
            print(f"❌ Error al conectar con Elastic: {e}")
            return False

    # ---------------------------------------------------------
    # ÍNDICES
    # ---------------------------------------------------------
    def crear_index(self, nombre_index: str, mappings: Dict = None, settings: Dict = None) -> bool:
        try:
            body = {}
            if mappings:
                body["mappings"] = mappings
            if settings:
                body["settings"] = settings

            self.client.indices.create(index=nombre_index, body=body)
            return True
        except Exception as e:
            print(f"Error al crear índice: {e}")
            return False

    def eliminar_index(self, nombre_index: str) -> bool:
        try:
            self.client.indices.delete(index=nombre_index)
            return True
        except Exception as e:
            print(f"Error al eliminar índice: {e}")
            return False

    def listar_indices(self) -> List[Dict]:
        try:
            indices_raw = self.client.cat.indices(
                format="json",
                h="index,docs.count,store.size,health,status"
            )

            return [
                {
                    "nombre": idx.get("index", ""),
                    "total_documentos": int(idx.get("docs.count", 0)) if str(idx.get("docs.count", "0")).isdigit() else 0,
                    "tamaño": idx.get("store.size", "0b"),
                    "salud": idx.get("health", "unknown"),
                    "estado": idx.get("status", "unknown"),
                }
                for idx in indices_raw
            ]

        except Exception as e:
            print(f"Error al listar índices: {e}")
            return []

    # ---------------------------------------------------------
    # DOCUMENTOS
    # ---------------------------------------------------------
    def indexar_documento(self, index: str, documento: Dict, doc_id: Optional[str] = None) -> bool:
        try:
            if doc_id:
                self.client.index(index=index, id=doc_id, document=documento)
            else:
                self.client.index(index=index, document=documento)
            return True
        except Exception as e:
            print(f"Error al indexar documento: {e}")
            return False

    def indexar_bulk(self, index: str, documentos: List[Dict]) -> Dict:
        try:
            acciones = [
                {"_index": index, "_source": doc}
                for doc in documentos
            ]

            success, errors = bulk(self.client, acciones, raise_on_error=False)

            return {
                "success": True,
                "indexados": success,
                "fallidos": len(errors) if errors else 0,
                "errores": errors or []
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def obtener_documento(self, index: str, doc_id: str) -> Optional[Dict]:
        try:
            response = self.client.get(index=index, id=doc_id)
            return response.get("_source")
        except Exception:
            return None

    def actualizar_documento(self, index: str, doc_id: str, datos: Dict) -> bool:
        try:
            self.client.update(index=index, id=doc_id, doc=datos)
            return True
        except Exception as e:
            print(f"Error al actualizar documento: {e}")
            return False

    def eliminar_documento(self, index: str, doc_id: str) -> bool:
        try:
            self.client.delete(index=index, id=doc_id)
            return True
        except Exception as e:
            print(f"Error al eliminar documento: {e}")
            return False

    # ---------------------------------------------------------
    # CONSULTAS / BÚSQUEDAS
    # ---------------------------------------------------------
    def buscar(self, index: str, query: Dict, aggs: Dict = None, size: int = 10) -> Dict:
        try:
            body = query.copy() if query else {}
            if aggs:
                body["aggs"] = aggs

            response = self.client.search(index=index, body=body, size=size)

            return {
                "success": True,
                "total": response["hits"]["total"]["value"],
                "resultados": response["hits"]["hits"],
                "aggs": response.get("aggregations", {})
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def buscar_texto(self, index: str, texto: str, campos: List[str] = None, size: int = 10) -> Dict:
        try:
            if campos:
                query = {
                    "query": {
                        "multi_match": {
                            "query": texto,
                            "fields": campos,
                            "type": "best_fields"
                        }
                    }
                }
            else:
                query = {
                    "query": {
                        "query_string": {"query": texto}
                    }
                }

            return self.buscar(index, query, size=size)

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ---------------------------------------------------------
    # EJECUTORES GENERALES (JSON Commands)
    # ---------------------------------------------------------
    def ejecutar_query(self, query_json: str) -> Dict:
        try:
            query = json.loads(query_json)
            index = query.pop("index", "_all")

            response = self.client.search(index=index, body=query)

            return {
                "success": True,
                "total": response["hits"]["total"]["value"],
                "hits": response["hits"]["hits"],
                "aggs": response.get("aggregations", {})
            }

        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON inválido: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def ejecutar_dml(self, comando_json: str) -> Dict:
        try:
            comando = json.loads(comando_json)
            op = comando.get("operacion")
            index = comando.get("index")

            if op in ("index", "create"):
                doc = comando.get("documento") or comando.get("body", {})
                doc_id = comando.get("id")
                resp = self.client.index(index=index, id=doc_id, document=doc)
                return {"success": True, "data": resp}

            if op == "update":
                resp = self.client.update(
                    index=index,
                    id=comando.get("id"),
                    doc=comando.get("doc")
                )
                return {"success": True, "data": resp}

            if op == "delete":
                resp = self.client.delete(index=index, id=comando.get("id"))
                return {"success": True, "data": resp}

            if op == "delete_by_query":
                q = comando.get("query", {})
                resp = self.client.delete_by_query(index=index, body={"query": q})
                return {"success": True, "data": resp}

            return {"success": False, "error": f"Operación no soportada: {op}"}

        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON inválido: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ---------------------------------------------------------
    def close(self):
        self.client.close()
