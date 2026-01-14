"""
Script para descargar un recurso desde la API de Passbolt usando autenticación GPGAuth.
Basado en la especificación OpenAPI del doc.yaml
"""

import os
import json
import uuid
import requests
import gnupg
from urllib.parse import unquote
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

PASSBOLT_URL = os.getenv('PASSBOLT_URL')
RESOURCE_ID = os.getenv('RESOURCE_ID')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
PASSPHRASE = os.getenv('PASSPHRASE')


class PassboltAPI:
    """Cliente para la API de Passbolt con autenticación GPGAuth (cookie-based)"""
    
    def __init__(self, base_url, private_key, passphrase):
        self.base_url = base_url.rstrip('/')
        self.private_key = private_key
        self.passphrase = passphrase
        self.session = requests.Session()  # Usar sesión para mantener cookies
        self.gpg = gnupg.GPG()
        
        # Importar la clave privada
        import_result = self.gpg.import_keys(self.private_key)
        if import_result.count == 0:
            raise Exception("No se pudo importar la clave privada PGP")
        
        self.key_fingerprint = import_result.fingerprints[0]
        print(f"✓ Clave PGP importada: {self.key_fingerprint}")
    
    def get_server_key(self):
        """Obtiene la clave pública del servidor"""
        url = f"{self.base_url}/auth/verify.json"
        response = self.session.get(url)
        response.raise_for_status()
        
        data = response.json()
        server_key = data['body']['keydata']
        server_fingerprint = data['body']['fingerprint']
        
        # Importar clave del servidor
        import_result = self.gpg.import_keys(server_key)
        print(f"✓ Clave del servidor importada: {server_fingerprint}")
        
        return server_fingerprint
    
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
        
        stage1_response = self.session.post(
            login_url,
            json=stage1_data,
            headers={"Content-Type": "application/json"}
        )
        stage1_response.raise_for_status()
        
        # El servidor devuelve un token encriptado en el header X-GPGAuth-User-Auth-Token
        server_token_encrypted = stage1_response.headers.get('X-GPGAuth-User-Auth-Token')
        if not server_token_encrypted:
            raise Exception("El servidor no devolvió el token de autenticación en X-GPGAuth-User-Auth-Token")
        
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
            raise Exception(f"Error al descifrar token del servidor: {decrypted_server_token.status}")
        
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
        
        stage2_response = self.session.post(
            login_url,
            json=stage2_data,
            headers={"Content-Type": "application/json"}
        )
        stage2_response.raise_for_status()
        
        # La sesión ahora tiene la cookie de autenticación (passbolt_session)
        print(f"✓ Login exitoso con GPGAuth!")
        print(f"  Cookie de sesión establecida")
        
    def get_resource_types(self):
        """Obtiene todos los tipos de recursos disponibles"""
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
    
    def get_resource_type_definition(self, resource_type_id):
        """Obtiene la definición de un tipo de recurso específico"""
        url = f"{self.base_url}/resource-types/{resource_type_id}.json"
        response = self.session.get(url)
        response.raise_for_status()
        
        data = response.json()
        return data['body']
        return True
    
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
        
        # Hacer la petición (usa la sesión con cookie de autenticación)
        response = self.session.get(url)
        response.raise_for_status()
        
        data = response.json()
        print(f"✓ Recurso descargado exitosamente")
        
        return data['body']
    
    def decrypt_secret(self, encrypted_secret):
        """Descifra un secreto encriptado"""
        if not encrypted_secret:
            return None
        
        decrypted = self.gpg.decrypt(encrypted_secret, passphrase=self.passphrase)
        if not decrypted.ok:
            raise Exception(f"Error al descifrar secreto: {decrypted.status}")
        
        return str(decrypted)
    
    def get_resource_type_details(self, resource_type_id):
        """
        Obtiene información detallada de un tipo de recurso específico
        
        Args:
            resource_type_id (str): ID del tipo de recurso
            
        Returns:
            dict: Información del tipo de recurso incluyendo campos personalizados
        """
        url = f"{self.base_url}/resource-types/{resource_type_id}.json"
        
        print(f"\n→ Obteniendo información del tipo de recurso {resource_type_id}...")
        
        response = self.session.get(url)
        response.raise_for_status()
        
        data = response.json()
        print(f"✓ Información del tipo de recurso obtenida")
        
        return data['body']


def main():
    """Función principal"""
    print("=" * 70)
    print("PASSBOLT - DESCARGA DE RECURSO")
    print("=" * 70)
    print()
    
    try:
        # Crear cliente API
        api = PassboltAPI(PASSBOLT_URL, PRIVATE_KEY, PASSPHRASE)
        
        # Login
        print("\n[1/3] Autenticación")
        print("-" * 70)
        api.login()
        
        # Obtener recurso
        print("\n[2/3] Descarga del recurso")
        print("-" * 70)
        resource = api.get_resource(
            RESOURCE_ID,
            include_secret=True,
            include_permissions=True
        )
        
        # Descifrar metadata si existe (recursos v5)
        decrypted_metadata = None
        if 'metadata' in resource and resource['metadata']:
            print("\n→ Descifrando metadata...")
            try:
                decrypted_metadata_str = api.decrypt_secret(resource['metadata'])
                decrypted_metadata = json.loads(decrypted_metadata_str)
                print(f"✓ Metadata descifrado")
            except Exception as e:
                print(f"✗ Error al descifrar metadata: {e}")
        
        # Mostrar información del recurso
        print("\n[3/3] Información del recurso")
        print("-" * 70)
        print(f"ID:          {resource.get('id')}")
        
        # Usar metadata descifrado si está disponible, sino usar campos directos
        if decrypted_metadata:
            print(f"Nombre:      {decrypted_metadata.get('name', 'N/A')}")
            print(f"Username:    {decrypted_metadata.get('username', 'N/A')}")
            uri_list = decrypted_metadata.get('uris', [])
            if uri_list and len(uri_list) > 0:
                # Puede ser un objeto con 'uri' o un string directo
                uri = uri_list[0].get('uri', 'N/A') if isinstance(uri_list[0], dict) else uri_list[0]
            else:
                uri = 'N/A'
            print(f"URI:         {uri}")
            print(f"Descripción: {decrypted_metadata.get('description', 'N/A')}")
        else:
            print(f"Nombre:      {resource.get('name', 'N/A')}")
            print(f"Username:    {resource.get('username', 'N/A')}")
            print(f"URI:         {resource.get('uri', 'N/A')}")
            print(f"Descripción: {resource.get('description', 'N/A')}")
        
        print(f"Tipo:        {resource.get('resource_type_id')}")
        print(f"Creado:      {resource.get('created')}")
        print(f"Modificado:  {resource.get('modified')}")
        
        # Si hay secretos, descifrarlos
        decrypted_secret = None
        if 'secrets' in resource and resource['secrets']:
            secret_data = resource['secrets'][0].get('data') if isinstance(resource['secrets'], list) else resource['secrets'].get('data')
            
            if secret_data:
                print("\n→ Descifrando secreto...")
                try:
                    decrypted_secret_str = api.decrypt_secret(secret_data)
                    print(f"✓ Secreto descifrado")
                    
                    # Intentar parsear como JSON
                    try:
                        decrypted_secret = json.loads(decrypted_secret_str)
                        print("\nContenido del secreto (JSON):")
                        for key, value in decrypted_secret.items():
                            print(f"  {key}: {value}")
                    except:
                        # Si no es JSON, crear un objeto con el contenido como texto
                        decrypted_secret = {"value": decrypted_secret_str}
                        print(f"\nContenido del secreto (texto plano):")
                        print(f"  {decrypted_secret_str}")
                        
                except Exception as e:
                    print(f"✗ Error al descifrar secreto: {e}")
        
        # Guardar JSON completo con datos descifrados
        output_file = f"resource_{RESOURCE_ID}.json"
        output_data = {
            "resource": resource,
            "decrypted_metadata": decrypted_metadata,
            "decrypted_secret": decrypted_secret
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Datos completos guardados en: {output_file}")
        print()
        print("=" * 70)
        print("✓ PROCESO COMPLETADO")
        print("=" * 70)
        
    except requests.exceptions.HTTPError as e:
        print(f"\n✗ Error HTTP: {e}")
        if hasattr(e.response, 'text'):
            print(f"  Respuesta: {e.response.text}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
