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
        print(f"[OK] Clave PGP importada: {self.key_fingerprint}")
    
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
        print(f"[OK] Clave del servidor importada: {server_fingerprint}")
        
        return server_fingerprint
    
    def login(self, user_id=None):
        """
        Realiza el login usando GPGAuth authentication (protocol legado con cookies)
        
        Stage 1: POST /auth/login.json - Obtener challenge token del servidor
        Stage 2: POST /auth/login.json - Enviar challenge descifrado y completar login
        """
        # Stage 1: Obtener challenge token del servidor
        print("> Solicitando token de autenticación...")
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
        
        print(f"[OK] Token recibido")
        
        # El token viene URL-encoded, necesitamos decodificarlo y limpiar escapes
        server_token_encrypted = unquote(server_token_encrypted)
        server_token_encrypted = server_token_encrypted.replace(r'\+', ' ').replace(r'\n', '\n')
        
        # Descifrar el token del servidor
        print("> Descifrando token...")
        decrypted_server_token = self.gpg.decrypt(
            server_token_encrypted,
            passphrase=self.passphrase
        )
        
        if not decrypted_server_token.ok:
            raise Exception(f"Error al descifrar token del servidor: {decrypted_server_token.status}")
        
        user_token = str(decrypted_server_token)
        print(f"[OK] Token descifrado")
        
        # Stage 2: Login final con el token descifrado
        print("> Completando autenticación...")
        
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
        print(f"[OK] Login exitoso con GPGAuth!")
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
        
        print(f"\n> Descargando recurso {resource_id}...")
        
        # Hacer la petición (usa la sesión con cookie de autenticación)
        response = self.session.get(url)
        response.raise_for_status()
        
        data = response.json()
        print(f"[OK] Recurso descargado exitosamente")
        
        return data['body']
    
    def decrypt_secret(self, encrypted_secret):
        """Descifra un secreto encriptado"""
        if not encrypted_secret:
            return None
        
        decrypted = self.gpg.decrypt(encrypted_secret, passphrase=self.passphrase)
        if not decrypted.ok:
            raise Exception(f"Error al descifrar secreto: {decrypted.status}")
        
        return str(decrypted)
    
    def decrypt_metadata(self, resource):
        """
        Descifra metadata, detectando automáticamente si es v4 (directo) o v5 (shared key)
        
        Args:
            resource (dict): El recurso completo con metadata y metadata_key_*
            
        Returns:
            dict: La metadata descifrada o None si no se pudo descifrar
        """
        metadata_blob = resource.get('metadata')
        if not metadata_blob:
            return None
        
        metadata_key_type = resource.get('metadata_key_type')
        metadata_key_id = resource.get('metadata_key_id')
        
        # Detectar tipo de metadata
        if metadata_key_type == 'shared_key' and metadata_key_id:
            # Metadata v5 con shared key
            print(f"> Detectada metadata v5 con shared_key")
            
            # Primero: intentar con session keys en cache
            print(f"> Verificando session keys en cache...")
            session_keys = self.get_metadata_session_keys()
            if session_keys and metadata_key_id in session_keys:
                try:
                    session_key_data = session_keys[metadata_key_id]
                    print(f"[OK] Session key encontrada en cache")
                    # Aquí usaríamos la session key para descifrar la metadata
                    # Por ahora, continuar con el método tradicional
                except Exception as e:
                    print(f"[WARN] Error con session key: {e}")
            
            # Segundo: intentar descifrado directo (algunos servidores mantienen compatibilidad)
            print(f"> Intentando descifrado directo como primer intento...")
            try:
                decrypted_str = self.decrypt_secret(metadata_blob)
                result = json.loads(decrypted_str)
                print(f"[OK] Metadata descifrada con método directo (compatibilidad v4)")
                return result
            except Exception as e_direct:
                print(f"[WARN] Descifrado directo falló: {e_direct}")
            
            # Tercero: intentar método v5 con shared key
            try:
                return self.decrypt_metadata_v5(metadata_blob, metadata_key_id)
            except Exception as e:
                print(f"[WARN] Fallo v5 shared key: {e}")
                return None
        else:
            # Metadata v4 o legacy (descifrado directo)
            print(f"> Detectada metadata v4/legacy (descifrado directo)")
            try:
                decrypted_str = self.decrypt_secret(metadata_blob)
                return json.loads(decrypted_str)
            except Exception as e:
                print(f"[ERROR] Error al descifrar metadata directa: {e}")
                return None
    
    def extract_field_names_from_metadata(self, metadata, custom_fields):
        """
        Extrae los nombres de los campos desde la metadata descifrada
        
        Args:
            metadata (dict): Metadata descifrada del recurso
            custom_fields (list): Lista de custom_fields del secreto
            
        Returns:
            dict: Mapeo de field_id -> field_name
        """
        field_mapping = {}
        
        if not metadata or not custom_fields:
            return field_mapping
        
        # Buscar definition o schema en metadata
        if 'resource_type_definition' in metadata:
            definition = metadata['resource_type_definition']
        elif 'schema' in metadata:
            definition = metadata['schema']
        elif 'fields' in metadata:
            definition = {'fields': metadata['fields']}
        else:
            # Buscar cualquier estructura que contenga fields
            definition = None
            for key, value in metadata.items():
                if isinstance(value, dict) and 'fields' in value:
                    definition = value
                    break
        
        if definition and 'fields' in definition:
            fields = definition['fields']
            for field in fields:
                if 'id' in field and 'label' in field:
                    field_mapping[field['id']] = field['label']
                elif 'id' in field and 'name' in field:
                    field_mapping[field['id']] = field['name']
        
        return field_mapping
    
    def get_metadata_session_keys(self):
        """
        Obtiene las session keys de metadata disponibles para el usuario actual
        
        Returns:
            dict: Session keys disponibles
        """
        try:
            url = f"{self.base_url}/metadata/session-keys.json"
            print(f"> Obteniendo metadata session keys...")
            
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            print(f"[OK] Session keys obtenidas")
            
            # DEBUG: Examinar la estructura completa de session keys
            if 'body' in data:
                body = data['body']
                print(f"[DEBUG] Session keys encontradas: {len(body) if isinstance(body, list) else 1}")
                
                if isinstance(body, list):
                    for i, sk in enumerate(body):
                        if isinstance(sk, dict):
                            print(f"[DEBUG] Session key {i}: {list(sk.keys())}")
                            
                            # Examinar contenido de 'data' si existe
                            if 'data' in sk:
                                data_content = sk['data']
                                print(f"[DEBUG] Session key {i} data tipo: {type(data_content)}")
                                print(f"[DEBUG] Session key {i} data longitud: {len(data_content) if isinstance(data_content, str) else 'N/A'}")
                                
                                # Verificar si es una clave PGP
                                if isinstance(data_content, str) and 'BEGIN PGP' in data_content:
                                    print(f"[DEBUG] Session key {i} contiene clave PGP, intentando importar...")
                                    try:
                                        # Primero intentar descifrar si está cifrada para nosotros
                                        if 'BEGIN PGP MESSAGE' in data_content:
                                            decrypt_result = self.gpg.decrypt(data_content, passphrase=self.passphrase)
                                            if decrypt_result.ok:
                                                decrypted_key = str(decrypt_result)
                                                print(f"[OK] Session key {i} descifrada")
                                                if 'BEGIN PGP PRIVATE KEY' in decrypted_key:
                                                    import_result = self.gpg.import_keys(decrypted_key)
                                                    if import_result.count > 0:
                                                        print(f"[OK] Clave privada de session key importada: {import_result.fingerprints[0]}")
                                        
                                        # Intentar importar directamente si es clave pública/privada
                                        elif 'BEGIN PGP PRIVATE KEY' in data_content or 'BEGIN PGP PUBLIC KEY' in data_content:
                                            import_result = self.gpg.import_keys(data_content)
                                            if import_result.count > 0:
                                                print(f"[OK] Clave de session key importada: {import_result.fingerprints[0]}")
                                                
                                    except Exception as e_import:
                                        print(f"[WARN] Error procesando session key {i}: {e_import}")
                            
                            # Importar cualquier clave privada que encontremos
                            if 'private_key' in sk:
                                try:
                                    print(f"[DEBUG] Importando session key privada {i}...")
                                    import_result = self.gpg.import_keys(sk['private_key'])
                                    if import_result.count > 0:
                                        print(f"[OK] Session key privada importada: {import_result.fingerprints[0]}")
                                except Exception as e_import:
                                    print(f"[WARN] Error importando session key: {e_import}")
            
            return data.get('body', {})
            
        except Exception as e:
            print(f"[WARN] No se pudieron obtener session keys: {e}")
            return {}
    
    def get_shared_key(self, metadata_key_id):
        """
        Obtiene una shared key para descifrar metadata v5
        
        Args:
            metadata_key_id (str): ID de la shared key
            
        Returns:
            str: La shared key cifrada para este usuario
        """
        # Probar endpoints oficiales de la documentación Passbolt v5
        endpoints_to_try = [
            # Endpoints oficiales según passbolt.yml
            f"/metadata/keys.json?filter[id]={metadata_key_id}&contain[metadata_private_keys]=1",
            f"/metadata/session-keys.json",
            f"/metadata/keys/{metadata_key_id}.json",
            # Endpoints legacy
            f"/metadata-keys/{metadata_key_id}.json",
            f"/resource-metadata-keys/{metadata_key_id}.json",
            f"/shared-keys/{metadata_key_id}.json",
            f"/metadata-keys.json?filter[id]={metadata_key_id}",
            f"/resources/metadata-keys/{metadata_key_id}.json",
            f"/shares/resource/{metadata_key_id}.json",
            f"/share/resource/{metadata_key_id}.json"
        ]
        
        for endpoint in endpoints_to_try:
            try:
                url = f"{self.base_url}{endpoint}"
                print(f"> Intentando obtener shared key desde: {endpoint}")
                
                response = self.session.get(url)
                response.raise_for_status()
                
                data = response.json()
                
                # Buscar la key cifrada para nuestro usuario en diferentes formatos
                if 'body' in data:
                    body = data['body']
                    
                    # Si body es una lista de metadata keys
                    if isinstance(body, list):
                        for key_entry in body:
                            # Buscar metadata_private_keys para nuestro user
                            if 'metadata_private_keys' in key_entry:
                                for private_key in key_entry['metadata_private_keys']:
                                    if 'data' in private_key:
                                        print(f"[OK] Shared key obtenida desde {endpoint}")
                                        return private_key['data']
                            elif 'data' in key_entry:
                                print(f"[OK] Shared key obtenida desde {endpoint}")
                                return key_entry['data']
                    
                    # Si body es un dict con metadata_private_keys
                    elif isinstance(body, dict):
                        if 'metadata_private_keys' in body:
                            for private_key in body['metadata_private_keys']:
                                if 'data' in private_key:
                                    print(f"[OK] Shared key obtenida desde {endpoint}")
                                    return private_key['data']
                        elif 'data' in body:
                            print(f"[OK] Shared key obtenida desde {endpoint}")
                            return body['data']
                        else:
                            # Buscar en cualquier key que tenga data
                            for key, value in body.items():
                                if isinstance(value, dict) and 'data' in value:
                                    print(f"[OK] Shared key obtenida desde {endpoint}")
                                    return value['data']
                                elif isinstance(value, str) and 'BEGIN PGP MESSAGE' in value:
                                    print(f"[OK] Shared key obtenida desde {endpoint}")
                                    return value
                                    
            except Exception as e:
                print(f"[WARN] Endpoint {endpoint} no disponible: {e}")
                continue
        
        raise Exception(f"No se pudo obtener la shared key {metadata_key_id} desde ningún endpoint conocido")
    
    def decrypt_metadata_v5(self, metadata_blob, metadata_key_id):
        """
        Descifra metadata v5 usando shared keys
        
        Args:
            metadata_blob (str): El blob de metadata cifrado
            metadata_key_id (str): ID de la shared key necesaria
            
        Returns:
            dict: La metadata descifrada como JSON
        """
        if not metadata_blob or not metadata_key_id:
            return None
            
        try:
            print(f"> Obteniendo shared key {metadata_key_id}...")
            
            # Paso 1: Obtener la shared key cifrada
            encrypted_shared_key = self.get_shared_key(metadata_key_id)
            
            # Paso 2: Descifrar la shared key con nuestra clave PGP
            print(f"> Descifrando shared key...")
            decrypted_shared_key_result = self.gpg.decrypt(
                encrypted_shared_key, 
                passphrase=self.passphrase
            )
            
            if not decrypted_shared_key_result.ok:
                raise Exception(f"Error al descifrar shared key: {decrypted_shared_key_result.status}")
            
            shared_key_data = str(decrypted_shared_key_result)
            print(f"[OK] Shared key descifrada")
            
            # PRIMERO: Intentar descifrar metadata directamente con clave del usuario
            print(f"> Intentando descifrado DIRECTO del metadata con clave del usuario...")
            try:
                direct_decrypt_result = self.gpg.decrypt(
                    metadata_blob,
                    passphrase=self.passphrase
                )
                
                if direct_decrypt_result.ok:
                    metadata_str = str(direct_decrypt_result)
                    print(f"[OK] Metadata descifrada DIRECTAMENTE con clave del usuario")
                    return json.loads(metadata_str)
                else:
                    print(f"[INFO] Descifrado directo del metadata falló: {direct_decrypt_result.status}")
            except Exception as e_direct_user:
                print(f"[INFO] Error descifrado directo del metadata: {e_direct_user}")
            
            # NUEVO: Intentar descifrado después de haber importado session keys
            print(f"> Reintentando descifrado directo después de importar session keys...")
            try:
                retry_decrypt_result = self.gpg.decrypt(
                    metadata_blob,
                    passphrase=self.passphrase
                )
                
                if retry_decrypt_result.ok:
                    metadata_str = str(retry_decrypt_result)
                    print(f"[OK] Metadata descifrada con session key importada")
                    return json.loads(metadata_str)
                else:
                    print(f"[INFO] Reintento de descifrado falló: {retry_decrypt_result.status}")
            except Exception as e_retry:
                print(f"[INFO] Error en reintento: {e_retry}")
            
            print(f"> Intentando descifrado del metadata usando la shared key...")
            
            # Paso 3: Usar la shared key para descifrar la metadata
            print(f"> Descifrando metadata con shared key...")
            
            # Intentar descifrado directo GPG primero
            try:
                decrypted_metadata_result = self.gpg.decrypt(
                    metadata_blob,
                    passphrase=self.passphrase
                )
                if decrypted_metadata_result.ok:
                    metadata_str = str(decrypted_metadata_result)
                    print(f"[OK] Metadata descifrada con GPG")
                    return json.loads(metadata_str)
            except:
                pass
            
            # Implementar descifrado simétrico AES para Passbolt v5
            try:
                # La shared key descifrada debería ser un JSON con la clave AES
                shared_key_json = json.loads(shared_key_data)
                print(f"[OK] Shared key parseada como JSON: {list(shared_key_json.keys())}")
                
                # Manejar estructura PGP nested en shared key
                if 'armored_key' in shared_key_json and 'passphrase' in shared_key_json:
                    print(f"[OK] Detectada shared key con estructura PGP nested")
                    print(f"[DEBUG] Shared key fingerprint: {shared_key_json.get('fingerprint', 'N/A')}")
                    
                    # Extraer la clave PGP y passphrase de la shared key
                    nested_pgp_key = shared_key_json['armored_key']
                    nested_passphrase = shared_key_json['passphrase']
                    
                    # Depurar metadata blob antes del descifrado
                    print(f"[DEBUG] Metadata blob tipo: {type(metadata_blob)}")
                    print(f"[DEBUG] Metadata blob longitud: {len(metadata_blob)}")
                    print(f"[DEBUG] Metadata blob inicio: {metadata_blob[:100]}...")
                    
                    if not metadata_blob or metadata_blob.strip() == "":
                        raise Exception("Metadata blob está vacío")
                    
                    # Verificar que es un mensaje PGP válido
                    if not metadata_blob.startswith('-----BEGIN PGP MESSAGE-----'):
                        print(f"[WARN] Metadata blob no parece ser PGP, intentando interpretación directa")
                        # Puede ser que esté en un formato diferente, intentar como JSON directo
                        try:
                            direct_metadata = json.loads(metadata_blob)
                            print(f"[OK] Metadata blob era JSON directo")
                            return direct_metadata
                        except:
                            raise Exception(f"Metadata blob no es PGP ni JSON válido")
                    
                    # Intentar múltiples enfoques para el descifrado
                    approaches = [
                        # 1. Usar clave nested directamente
                        lambda: self._decrypt_with_nested_key(metadata_blob, nested_pgp_key, nested_passphrase),
                        # 2. Usar clave actual con passphrase nested (por si la shared key es la passphrase)
                        lambda: self._decrypt_with_current_key(metadata_blob, nested_passphrase),
                        # 3. Intentar interpretar como datos ya descifrados
                        lambda: self._try_direct_interpretation(metadata_blob, shared_key_json)
                    ]
                    
                    for i, approach in enumerate(approaches, 1):
                        try:
                            print(f"[DEBUG] Intentando enfoque {i}...")
                            result = approach()
                            if result:
                                print(f"[OK] Metadata descifrada con enfoque {i}")
                                return result
                        except Exception as e_approach:
                            print(f"[WARN] Enfoque {i} falló: {e_approach}")
                            continue
                    
                    raise Exception("Todos los enfoques de descifrado fallaron")
                
                # Búsqueda de clave AES en otros campos si no es estructura PGP
                aes_key_b64 = None
                if 'key' in shared_key_json:
                    aes_key_b64 = shared_key_json['key']
                elif 'data' in shared_key_json:
                    aes_key_b64 = shared_key_json['data']
                else:
                    # Buscar cualquier campo que parezca una clave base64
                    for k, v in shared_key_json.items():
                        if isinstance(v, str) and len(v) > 20:
                            aes_key_b64 = v
                            break
                
                if not aes_key_b64:
                    raise Exception("No se encontró clave AES en shared key")
                    
                # Decodificar la clave AES
                import base64
                try:
                    aes_key = base64.b64decode(aes_key_b64)
                    print(f"[OK] Clave AES extraída ({len(aes_key)} bytes)")
                except Exception as e_b64:
                    print(f"[WARN] Error base64: {e_b64}, intentando padding")
                    # Añadir padding si es necesario
                    padded_key = aes_key_b64 + '=' * (4 - len(aes_key_b64) % 4)
                    aes_key = base64.b64decode(padded_key)
                    print(f"[OK] Clave AES extraída con padding ({len(aes_key)} bytes)")
                
                # El metadata blob puede estar en formato "data:iv:ciphertext" o similar
                # Analizar el formato del metadata blob
                if metadata_blob.startswith('-----BEGIN'):
                    # Es un mensaje PGP, intentar con GPG otra vez pero con la clave descifrada
                    raise Exception("Metadata en formato PGP no manejado con clave simétrica")
                
                # Intentar diferentes formatos de metadata blob
                metadata_parts = None
                if ':' in metadata_blob:
                    # Formato "iv:ciphertext" o "data:iv:ciphertext"
                    parts = metadata_blob.split(':')
                    if len(parts) >= 2:
                        metadata_parts = parts
                        print(f"[OK] Metadata blob dividido en {len(parts)} partes")
                
                if metadata_parts:
                    # Intentar formato "iv:ciphertext"
                    try:
                        iv_b64 = metadata_parts[0] if len(metadata_parts) == 2 else metadata_parts[1]
                        ciphertext_b64 = metadata_parts[1] if len(metadata_parts) == 2 else metadata_parts[2]
                        
                        iv = base64.b64decode(iv_b64)
                        ciphertext = base64.b64decode(ciphertext_b64)
                        
                        print(f"[OK] IV ({len(iv)} bytes) y ciphertext ({len(ciphertext)} bytes) extraídos")
                        
                        # Intentar descifrado AES-GCM primero
                        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                        try:
                            aesgcm = AESGCM(aes_key)
                            # Para AES-GCM, el ciphertext incluye el tag
                            if len(ciphertext) > 16:  # Al menos tag de 16 bytes
                                plaintext = aesgcm.decrypt(iv, ciphertext, None)
                                metadata_str = plaintext.decode('utf-8')
                                print(f"[OK] Metadata descifrada con AES-GCM")
                                return json.loads(metadata_str)
                        except Exception as e_gcm:
                            print(f"[WARN] AES-GCM falló: {e_gcm}")
                        
                        # Intentar descifrado AES-CBC
                        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                        from cryptography.hazmat.backends import default_backend
                        from cryptography.hazmat.primitives import padding
                        
                        try:
                            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
                            decryptor = cipher.decryptor()
                            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
                            
                            # Remover padding PKCS7
                            unpadder = padding.PKCS7(128).unpadder()
                            plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
                            
                            metadata_str = plaintext.decode('utf-8')
                            print(f"[OK] Metadata descifrada con AES-CBC")
                            return json.loads(metadata_str)
                            
                        except Exception as e_cbc:
                            print(f"[WARN] AES-CBC falló: {e_cbc}")
                    
                    except Exception as e_format:
                        print(f"[WARN] Error procesando formato metadata: {e_format}")
                
                else:
                    # Metadata blob como base64 directo
                    try:
                        ciphertext = base64.b64decode(metadata_blob)
                        print(f"[OK] Metadata blob decodificado ({len(ciphertext)} bytes)")
                        
                        # Sin IV explícito, intentar con IV de zeros o extraer del ciphertext
                        if len(ciphertext) >= 16:
                            # IV puede estar al inicio del ciphertext
                            iv = ciphertext[:16]
                            actual_ciphertext = ciphertext[16:]
                            
                            # Intentar AES-CBC
                            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
                            decryptor = cipher.decryptor()
                            padded_plaintext = decryptor.update(actual_ciphertext) + decryptor.finalize()
                            
                            unpadder = padding.PKCS7(128).unpadder()
                            plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
                            
                            metadata_str = plaintext.decode('utf-8')
                            print(f"[OK] Metadata descifrada con AES-CBC (IV del ciphertext)")
                            return json.loads(metadata_str)
                            
                    except Exception as e_direct:
                        print(f"[WARN] Descifrado directo falló: {e_direct}")
                        
            except json.JSONDecodeError:
                print(f"[WARN] Shared key no es JSON válido")
                # Intentar como clave binaria directa
                try:
                    import base64
                    aes_key = base64.b64decode(shared_key_data)
                    print(f"[OK] Shared key tratada como base64 directo ({len(aes_key)} bytes)")
                    # Continuar con lógica similar...
                except:
                    print(f"[ERROR] No se pudo procesar shared key en ningún formato conocido")
            except Exception as e:
                print(f"[ERROR] Error en descifrado simétrico: {e}")
                import traceback
                traceback.print_exc()
                
            return None
            
        except Exception as e:
            print(f"[ERROR] Error al descifrar metadata v5: {e}")
            return None

    def _decrypt_with_nested_key(self, metadata_blob, nested_pgp_key, nested_passphrase):
        """Intenta descifrar usando la clave PGP nested"""
        # Importar la clave PGP nested temporalmente
        import_result = self.gpg.import_keys(nested_pgp_key)
        if import_result.count == 0:
            raise Exception("No se pudo importar la clave PGP nested")
        
        nested_fingerprint = import_result.fingerprints[0]
        
        try:
            # Descifrar usando la clave nested
            decrypted_result = self.gpg.decrypt(
                metadata_blob,
                passphrase=nested_passphrase
            )
            
            if decrypted_result.ok:
                metadata_str = str(decrypted_result)
                return json.loads(metadata_str)
            else:
                raise Exception(f"Error GPG nested: {decrypted_result.status}")
                
        finally:
            # Limpiar la clave temporal
            try:
                self.gpg.delete_keys(nested_fingerprint, secret=True, passphrase=nested_passphrase)
                self.gpg.delete_keys(nested_fingerprint)
            except:
                pass
    
    def _decrypt_with_current_key(self, metadata_blob, alternative_passphrase):
        """Intenta descifrar usando la clave actual con passphrase alternativa"""
        decrypted_result = self.gpg.decrypt(
            metadata_blob,
            passphrase=alternative_passphrase
        )
        
        if decrypted_result.ok:
            metadata_str = str(decrypted_result)
            return json.loads(metadata_str)
        else:
            raise Exception(f"Error GPG con passphrase alternativa: {decrypted_result.status}")
    
    def _try_direct_interpretation(self, metadata_blob, shared_key_json):
        """Intenta interpretar los datos de manera directa sin PGP"""
        # Si la shared key contiene datos útiles para descifrado simétrico
        if 'passphrase' in shared_key_json:
            passphrase = shared_key_json['passphrase']
            print(f"[DEBUG] Intentando descifrado simétrico con passphrase de la shared key")
            
            # Verificar si el passphrase es una clave AES o similar
            try:
                from cryptography.fernet import Fernet
                import base64
                
                # Intentar usar el passphrase como clave Fernet
                if len(passphrase) >= 32:  # Al menos 32 chars para una clave válida
                    # Intentar interpretarlo como base64 de una clave
                    try:
                        key_bytes = base64.b64decode(passphrase + "==")[:32]  # Padding if needed
                        fernet_key = base64.urlsafe_b64encode(key_bytes)
                        f = Fernet(fernet_key)
                        
                        # Intentar descifrar como Fernet
                        if metadata_blob.startswith('-----BEGIN PGP MESSAGE-----'):
                            # Extraer el contenido del mensaje PGP sin descifrar
                            pgp_lines = metadata_blob.split('\n')
                            pgp_content = ''.join([line for line in pgp_lines 
                                                 if not line.startswith('-----') and line.strip()])
                            
                            # Intentar como base64
                            encrypted_data = base64.b64decode(pgp_content)
                            decrypted_data = f.decrypt(encrypted_data)
                            return json.loads(decrypted_data.decode('utf-8'))
                            
                    except Exception as e_fernet:
                        print(f"[DEBUG] Fernet falló: {e_fernet}")
                        pass
            except ImportError:
                pass
        
        raise Exception("No se pudo interpretar los datos directamente")

    def get_resource_type_details(self, resource_type_id):
        """
        Obtiene información detallada de un tipo de recurso específico
        
        Args:
            resource_type_id (str): ID del tipo de recurso
            
        Returns:
            dict: Información del tipo de recurso incluyendo campos personalizados
        """
        url = f"{self.base_url}/resource-types/{resource_type_id}.json"
        
        print(f"\n> Obteniendo información del tipo de recurso {resource_type_id}...")
        
        response = self.session.get(url)
        response.raise_for_status()
        
        data = response.json()
        print(f"[OK] Información del tipo de recurso obtenida")
        
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
            print("\n> Descifrando metadata...")
            try:
                decrypted_metadata_str = api.decrypt_secret(resource['metadata'])
                decrypted_metadata = json.loads(decrypted_metadata_str)
                print(f"[OK] Metadata descifrado")
            except Exception as e:
                print(f"[ERROR] Error al descifrar metadata: {e}")
        
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
                print("\n> Descifrando secreto...")
                try:
                    decrypted_secret_str = api.decrypt_secret(secret_data)
                    print(f"[OK] Secreto descifrado")
                    
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
                    print(f"[ERROR] Error al descifrar secreto: {e}")
        
        # Guardar JSON completo con datos descifrados
        output_file = f"resource_{RESOURCE_ID}.json"
        output_data = {
            "resource": resource,
            "decrypted_metadata": decrypted_metadata,
            "decrypted_secret": decrypted_secret
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n[OK] Datos completos guardados en: {output_file}")
        print()
        print("=" * 70)
        print("[OK] PROCESO COMPLETADO")
        print("=" * 70)
        
    except requests.exceptions.HTTPError as e:
        print(f"\n[ERROR] Error HTTP: {e}")
        if hasattr(e.response, 'text'):
            print(f"  Respuesta: {e.response.text}")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
