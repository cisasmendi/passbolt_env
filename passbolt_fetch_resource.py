"""
Cliente para la API de Passbolt con autenticación GPGAuth
Basado en la especificación OpenAPI del doc.yaml
"""

import json
import requests
import gnupg
from urllib.parse import unquote

from config import config
from exceptions import AuthenticationError, DecryptionError


class PassboltAPI:
    """Cliente para la API de Passbolt con autenticación GPGAuth (cookie-based)"""
    
    def __init__(self, base_url=None, private_key=None, passphrase=None):
        # Usar configuración global si no se proporcionan parámetros
        self.base_url = (base_url or config.passbolt_url).rstrip('/')
        self.private_key = private_key or config.private_key
        self.passphrase = passphrase or config.passphrase
        
        self.session = requests.Session()
        self.gpg = gnupg.GPG()
        self.key_fingerprint = None
        
        self._setup_gpg_key()
    
    def _setup_gpg_key(self):
        """Configura e importa la clave PGP"""
        import_result = self.gpg.import_keys(self.private_key)
        if import_result.count == 0:
            raise AuthenticationError("No se pudo importar la clave privada PGP")
        
        self.key_fingerprint = import_result.fingerprints[0]
        print(f"✓ Clave PGP importada: {self.key_fingerprint}")
    
    def get_server_key(self):
        """Obtiene la clave pública del servidor"""
        try:
            url = f"{self.base_url}/auth/verify.json"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            server_key = data['body']['keydata']
            server_fingerprint = data['body']['fingerprint']
            
            # Importar clave del servidor
            import_result = self.gpg.import_keys(server_key)
            if import_result.count == 0:
                raise AuthenticationError("No se pudo importar la clave del servidor")
            
            print(f"✓ Clave del servidor importada: {server_fingerprint}")
            return server_fingerprint
            
        except requests.RequestException as e:
            raise AuthenticationError(f"Error al obtener clave del servidor: {e}")
    
    def login(self, user_id=None):
        """
        Realiza el login usando GPGAuth authentication (protocol legado con cookies)
        
        Stage 1: POST /auth/login.json - Obtener challenge token del servidor
        Stage 2: POST /auth/login.json - Enviar challenge descifrado y completar login
        """
        # Stage 1: Obtener challenge token del servidor
        print("→ Solicitando token de autenticación...")
        login_url = f"{self.base_url}/auth/login.json"
        
        stage1_data = {
            "data": {
                "gpg_auth": {
                    "keyid": self.key_fingerprint
                }
            }
        }
        
        try:
            stage1_response = self.session.post(
                login_url,
                json=stage1_data,
                headers={"Content-Type": "application/json"}
            )
            stage1_response.raise_for_status()
            
            # El servidor devuelve un token encriptado en el header X-GPGAuth-User-Auth-Token
            server_token_encrypted = stage1_response.headers.get('X-GPGAuth-User-Auth-Token')
            if not server_token_encrypted:
                raise AuthenticationError("El servidor no devolvió el token de autenticación en X-GPGAuth-User-Auth-Token")
            
            print(f"✓ Token recibido")
            
            # El token viene URL-encoded, necesitamos decodificarlo y limpiar escapes
            server_token_encrypted = unquote(server_token_encrypted)
            server_token_encrypted = server_token_encrypted.replace(r'\+', ' ').replace(r'\n', '\n')
            
            # Descifrar el token del servidor
            print("→ Descifrando token...")
            decrypted_server_token = self.gpg.decrypt(
                server_token_encrypted,
                passphrase=self.passphrase
            )
            
            if not decrypted_server_token.ok:
                raise DecryptionError(f"Error al descifrar token del servidor: {decrypted_server_token.status}")
        
        except Exception as e:
            if isinstance(e, (AuthenticationError, DecryptionError)):
                raise
            raise AuthenticationError(f"Error durante el proceso de autenticación: {e}")
        
        user_token = str(decrypted_server_token)
        print(f"✓ Token descifrado")
        
        # Stage 2: Login final con el token descifrado
        print("→ Completando autenticación...")
        
        stage2_data = {
            "data": {
                "gpg_auth": {
                    "keyid": self.key_fingerprint,
                    "user_token_result": user_token
                }
            }
        }
        
        try:
            stage2_response = self.session.post(
                login_url,
                json=stage2_data,
                headers={"Content-Type": "application/json"}
            )
            stage2_response.raise_for_status()
            
            # La sesión ahora tiene la cookie de autenticación (passbolt_session)
            print(f"✓ Login exitoso con GPGAuth!")
            print(f"  Cookie de sesión establecida")
            
        except requests.RequestException as e:
            raise AuthenticationError(f"Error en el segundo stage del login: {e}")
        
    def get_resource_types(self):
        """Obtiene todos los tipos de recursos disponibles"""
        try:
            url = f"{self.base_url}/resource-types.json"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            resource_types = data['body']
            
            # Crear mapeo de ID a nombre y configuración
            types_map = {}
            for rt in resource_types:
                types_map[rt['id']] = {
                    'name': rt.get('name', 'Unknown'),
                    'slug': rt.get('slug', 'unknown'),
                    'definition': rt.get('definition', {})
                }
            
            return types_map
            
        except requests.RequestException as e:
            raise Exception(f"Error al obtener tipos de recursos: {e}")
    
    def get_resource_type_definition(self, resource_type_id):
        """Obtiene la definición de un tipo de recurso específico"""
        try:
            url = f"{self.base_url}/resource-types/{resource_type_id}.json"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            return data['body']
            
        except requests.RequestException as e:
            raise Exception(f"Error al obtener definición del tipo de recurso: {e}")
    
    def get_resource(self, resource_id, include_secret=True, include_permissions=False):
        """
        Obtiene un recurso por su ID
        
        Args:
            resource_id: UUID del recurso
            include_secret: Incluir el secreto encriptado
            include_permissions: Incluir permisos del recurso
        
        Returns:
            dict: Datos del recurso
        """
        # Construir URL con parámetros
        url = f"{self.base_url}/resources/{resource_id}.json"
        params = []
        
        if include_secret:
            params.append("contain[secret]=1")
        if include_permissions:
            params.append("contain[permissions]=1")
        
        if params:
            url += "?" + "&".join(params)
        
        print(f"\n→ Descargando recurso {resource_id}...")
        
        try:
            # Hacer la petición (usa la sesión con cookie de autenticación)
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            print(f"✓ Recurso descargado exitosamente")
            
            return data['body']
            
        except requests.RequestException as e:
            if response.status_code == 404:
                raise Exception(f"Recurso {resource_id} no encontrado")
            raise Exception(f"Error al obtener recurso: {e}")
    
    def decrypt_secret(self, encrypted_secret):
        """Descifra un secreto encriptado"""
        if not encrypted_secret:
            return None
        
        try:
            decrypted = self.gpg.decrypt(encrypted_secret, passphrase=self.passphrase)
            if not decrypted.ok:
                raise DecryptionError(f"Error al descifrar secreto: {decrypted.status}")
            
            return str(decrypted)
            
        except Exception as e:
            if isinstance(e, DecryptionError):
                raise
            raise DecryptionError(f"Error durante el descifrado: {e}")


# Para compatibilidad con versiones anteriores
if __name__ == "__main__":
    print("Este módulo ha sido refactorizado.")
    print("Usa 'python passbolt_cli.py' para la funcionalidad completa.")