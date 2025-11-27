from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from typing import Dict, List, Optional
import hashlib


class MongoDB:
    """Manejador de conexión y operaciones con MongoDB."""

    def __init__(self, uri: str, db_name: str):
        """Inicializa la conexión con MongoDB."""
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

    # ---------------------------------------------------------
    # CONEXIÓN
    # ---------------------------------------------------------
    def test_connection(self) -> bool:
        """Verifica que MongoDB esté disponible."""
        try:
            self.client.admin.command("ping")
            return True
        except ConnectionFailure:
            return False

    # ---------------------------------------------------------
    # USUARIOS
    # ---------------------------------------------------------
    def validar_usuario(self, usuario: str, password: str, coleccion: str) -> Optional[Dict]:
        """Valida un usuario en la base de datos.

        **MD5 está deshabilitado** para pruebas.
        """
        try:
            # password_md5 = hashlib.md5(password.encode()).hexdigest()
            password_validado = password  # Mantener plano para compatibilidad

            return self.db[coleccion].find_one({
                "usuario": usuario,
                "password": password_validado
            })

        except Exception as e:
            print(f"Error al validar usuario: {e}")
            return None

    def obtener_usuario(self, usuario: str, coleccion: str) -> Optional[Dict]:
        """Obtiene un usuario por su nombre."""
        try:
            return self.db[coleccion].find_one({"usuario": usuario})
        except Exception as e:
            print(f"Error al obtener usuario: {e}")
            return None

    def listar_usuarios(self, coleccion: str) -> List[Dict]:
        """Retorna la lista completa de usuarios."""
        try:
            return list(self.db[coleccion].find({}))
        except Exception as e:
            print(f"Error al listar usuarios: {e}")
            return []

    def crear_usuario(self, usuario: str, password: str, permisos: Dict, coleccion: str) -> bool:
        """Crea un nuevo usuario.

        **MD5 está deshabilitado** para pruebas.
        """
        try:
            # password_md5 = hashlib.md5(password.encode()).hexdigest()
            password_guardado = password

            documento = {
                "usuario": usuario,
                "password": password_guardado,
                "permisos": permisos
            }

            self.db[coleccion].insert_one(documento)
            return True

        except Exception as e:
            print(f"Error al crear usuario: {e}")
            return False

    def actualizar_usuario(self, usuario: str, nuevos_datos: Dict, coleccion: str) -> bool:
        """Actualiza un usuario existente."""
        try:
            self.db[coleccion].update_one(
                {"usuario": usuario},
                {"$set": nuevos_datos}
            )
            return True

        except Exception as e:
            print(f"Error al actualizar usuario: {e}")
            return False

    def eliminar_usuario(self, usuario: str, coleccion: str) -> bool:
        """Elimina un usuario por nombre."""
        try:
            resultado = self.db[coleccion].delete_one({"usuario": usuario})
            return resultado.deleted_count > 0

        except Exception as e:
            print(f"Error al eliminar usuario: {e}")
            return False

    # ---------------------------------------------------------
    # CIERRE
    # ---------------------------------------------------------
    def close(self):
        """Cierra la conexión con MongoDB."""
        try:
            self.client.close()
        except:
            pass
