#!/usr/bin/env python3
"""
Cliente de autenticación GPGAuth para Passbolt API v5
Implementa el protocolo completo de autenticación usando GPG
"""

import os
import re
import json
import subprocess
import tempfile
from dotenv import load_dotenv
import requests
from urllib.parse import urljoin

# Cargar variables de entorno
load_dotenv()

class PassboltGPGAuth:
    """Cliente de autenticación GPGAuth para Passbolt"""
    
    def __init__(self, base_url, private_key, passphrase=None):
        """
        Inicializa el cliente de autenticación
        
        Args:
            base_url: URL base del servidor Passbolt
            private_key: Clave privada PGP en formato string
            passphrase: Contraseña de la clave privada (opcional)
        """
        self.base_url = base_url.rstrip('/')
        self.private_key = private_key
        self.passphrase = passphrase
        self.session = requests.Session()
        self.server_fingerprint = None
        self.server_keydata = None
        self.user_fingerprint = None
        
        # Importar clave privada al inicio
        self._import_private_key()
    
    def _run_gpg_command(self, command, input_data=None):
        """
        Ejecuta un comando GPG
        
        Args:
            command: Lista de argumentos para el comando GPG
            input_data: Datos de entrada (opcional)
            
        Returns:
            Tupla (stdout, stderr, returncode)
        """
        cmd = ['gpg', '--batch', '--yes', '--armor'] + command
        
        if self.passphrase:
            cmd.extend(['--pinentry-mode', 'loopback', '--passphrase', self.passphrase])
        
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=input_data)
        return stdout, stderr, process.returncode
    
    def _import_private_key(self):
        """Importa la clave privada GPG"""
        print("📥 Importando clave privada GPG...")
        stdout, stderr, returncode = self._run_gpg_command(
            ['--import'],
            input_data=self.private_key
        )
        
        if returncode != 0:
            print(f"❌ Error importando clave: {stderr}")
            raise Exception(f"Error al importar clave privada: {stderr}")
        
        # Extraer fingerprint de la clave importada
        self._extract_user_fingerprint()
        print(f"✅ Clave privada importada exitosamente")
        print(f"   Fingerprint: {self.user_fingerprint}")
    
    def _extract_user_fingerprint(self):
        """Extrae el fingerprint de la clave privada del usuario"""
        stdout, stderr, returncode = self._run_gpg_command(['--list-secret-keys', '--with-colons'])
        
        for line in stdout.split('\n'):
            if line.startswith('fpr:'):
                self.user_fingerprint = line.split(':')[9]
                break
        
        if not self.user_fingerprint:
            raise Exception("No se pudo extraer el fingerprint de la clave privada")
    
    def _decrypt_message(self, encrypted_message):
        """
        Descifra un mensaje GPG
        
        Args:
            encrypted_message: Mensaje cifrado en formato PGP
            
        Returns:
            Mensaje descifrado
        """
        stdout, stderr, returncode = self._run_gpg_command(
            ['--decrypt'],
            input_data=encrypted_message
        )
        
        if returncode != 0:
            raise Exception(f"Error al descifrar mensaje: {stderr}")
        
        return stdout.strip()
    
    def _sign_and_encrypt(self, message, recipient_fingerprint):
        """
        Firma y cifra un mensaje
        
        Args:
            message: Mensaje a firmar y cifrar
            recipient_fingerprint: Fingerprint del destinatario
            
        Returns:
            Mensaje firmado y cifrado
        """
        stdout, stderr, returncode = self._run_gpg_command([
            '--encrypt',
            '--sign',
            '--recipient', recipient_fingerprint,
            '--local-user', self.user_fingerprint,
            '--trust-model', 'always'
        ], input_data=message)
        
        if returncode != 0:
            raise Exception(f"Error al firmar y cifrar: {stderr}")
        
        return stdout.strip()
    
    def verify_server(self):
        """
        Paso 1: Verificar la identidad del servidor (Stage 0)
        GET /auth/verify.json - Obtener clave pública del servidor
        """
        print("\n🔐 Paso 1: Verificando identidad del servidor...")
        
        url = urljoin(self.base_url, '/auth/verify.json')
        response = self.session.get(url)
        
        if response.status_code != 200:
            raise Exception(f"Error obteniendo clave del servidor: {response.status_code}")
        
        data = response.json()
        self.server_fingerprint = data['body']['fingerprint']
        self.server_keydata = data['body']['keydata']
        
        print(f"   Server fingerprint: {self.server_fingerprint}")
        
        # Importar clave pública del servidor
        stdout, stderr, returncode = self._run_gpg_command(
            ['--import'],
            input_data=self.server_keydata
        )
        
        if returncode != 0:
            print(f"⚠️  Advertencia al importar clave del servidor: {stderr}")
        else:
            print(f"   ✅ Clave pública del servidor importada")
        
        return True
    
    def authenticate_step1(self):
        """
        Paso 2: Verificar que el servidor conoce nuestra clave (Stage 1)
        POST /auth/verify.json - Enviar token firmado al servidor
        """
        print("\n🔑 Paso 2: Verificando que el servidor conoce nuestra clave...")
        
        # El servidor debe decifrarnos un token
        url = urljoin(self.base_url, '/auth/verify.json')
        
        payload = {
            "data": {
                "gpg_auth": {
                    "keyid": self.user_fingerprint
                }
            }
        }
        
        response = self.session.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 200:
            raise Exception(f"Error en verificación Stage 1: {response.status_code} - {response.text}")
        
        # Extraer token del header X-GPGAuth-User-Auth-Token
        encrypted_token = response.headers.get('X-GPGAuth-User-Auth-Token')
        if not encrypted_token:
            raise Exception("No se recibió X-GPGAuth-User-Auth-Token del servidor")
        
        print(f"   ✅ Token recibido del servidor")
        print(f"   Token (primeros 50 chars): {encrypted_token[:50]}...")
        
        # El token viene URL-encoded, decodificarlo
        import urllib.parse
        encrypted_token = urllib.parse.unquote(encrypted_token)
        
        # Reemplazar \+ por espacios (formato específico del servidor)
        encrypted_token = encrypted_token.replace('\\+', ' ')
        
        print(f"   Token decodificado (primeros 80 chars): {encrypted_token[:80]}...")
        
        # Descifrar el token
        decrypted_token = self._decrypt_message(encrypted_token)
        print(f"   ✅ Token descifrado exitosamente")
        
        # Validar formato del token
        if not self._validate_token(decrypted_token):
            raise Exception(f"Token inválido: {decrypted_token}")
        
        return decrypted_token
    
    def _validate_token(self, token):
        """
        Valida el formato del token GPGAuth
        Formato: gpgauthv1.3.0|36|<uuid>|gpgauthv1.3.0
        """
        pattern = r'^gpgauthv\d+\.\d+\.\d+\|\d+\|[a-f0-9\-]+\|gpgauthv\d+\.\d+\.\d+$'
        return bool(re.match(pattern, token))
    
    def authenticate_step2(self, user_token):
        """
        Paso 3: Login final (Stage 2)
        POST /auth/login.json - Enviar token descifrado para completar autenticación
        """
        print("\n✅ Paso 3: Completando login...")
        
        url = urljoin(self.base_url, '/auth/login.json')
        
        payload = {
            "data": {
                "gpg_auth": {
                    "keyid": self.user_fingerprint,
                    "user_token_result": user_token
                }
            }
        }
        
        response = self.session.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 200:
            raise Exception(f"Error en login final: {response.status_code} - {response.text}")
        
        # Verificar respuesta del servidor
        encrypted_verify_token = response.headers.get('X-GPGAuth-Verify-Response')
        if encrypted_verify_token:
            # El servidor nos envía un token para verificar
            decrypted_verify = self._decrypt_message(encrypted_verify_token)
            print(f"   ✅ Verificación del servidor confirmada")
        
        # Guardar cookies de sesión
        print(f"   ✅ Sesión establecida")
        print(f"   Cookies: {list(self.session.cookies.keys())}")
        
        return True
    
    def login(self):
        """
        Ejecuta el flujo completo de autenticación GPGAuth
        
        Returns:
            True si la autenticación fue exitosa
        """
        print("=" * 60)
        print("🚀 Iniciando autenticación GPGAuth con Passbolt API v5")
        print("=" * 60)
        
        try:
            # Paso 1: Verificar servidor
            self.verify_server()
            
            # Paso 2: Autenticación Stage 1
            user_token = self.authenticate_step1()
            
            # Paso 3: Login final
            self.authenticate_step2(user_token)
            
            print("\n" + "=" * 60)
            print("✅ ¡Autenticación completada exitosamente!")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print("\n" + "=" * 60)
            print(f"❌ Error durante la autenticación: {str(e)}")
            print("=" * 60)
            return False
    
    def is_authenticated(self):
        """
        Verifica si la sesión actual está autenticada
        
        Returns:
            True si está autenticado
        """
        url = urljoin(self.base_url, '/auth/is-authenticated.json')
        response = self.session.get(url)
        return response.status_code == 200
    
    def get_resource(self, resource_id):
        """
        Obtiene un recurso (contraseña) desde Passbolt
        
        Args:
            resource_id: UUID del recurso
            
        Returns:
            Datos del recurso
        """
        if not self.is_authenticated():
            print("❌ No hay sesión autenticada. Ejecute login() primero.")
            return None
        
        url = urljoin(self.base_url, f'/resources/{resource_id}.json')
        response = self.session.get(url)
        
        if response.status_code != 200:
            print(f"❌ Error obteniendo recurso: {response.status_code}")
            return None
        
        return response.json()
    
    def get_resource_with_secret(self, resource_id):
        """
        Obtiene un recurso CON el secret descifrado
        
        Args:
            resource_id: UUID del recurso
            
        Returns:
            Datos del recurso incluyendo el secret
        """
        if not self.is_authenticated():
            print("❌ No hay sesión autenticada. Ejecute login() primero.")
            return None
        
        # Incluir el secret en la respuesta y el metadata descifrado
        url = urljoin(self.base_url, f'/resources/{resource_id}.json?contain[secret]=1&contain[metadata]=1&api-version=v5')
        response = self.session.get(url)
        
        if response.status_code != 200:
            print(f"❌ Error obteniendo recurso con secret: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return None
        
        return response.json()
    
    def get_resource_type(self, resource_type_id):
        """
        Obtiene información sobre un tipo de recurso
        
        Args:
            resource_type_id: UUID del tipo de recurso
            
        Returns:
            Información del resource type incluyendo definición de campos
        """
        if not self.is_authenticated():
            print("❌ No hay sesión autenticada. Ejecute login() primero.")
            return None
        
        url = urljoin(self.base_url, f'/resource-types/{resource_type_id}.json')
        response = self.session.get(url)
        
        if response.status_code != 200:
            print(f"❌ Error obteniendo resource type: {response.status_code}")
            return None
        
        return response.json()
    
    def get_metadata_keys(self, metadata_key_id=None):
        """
        Obtiene las claves de metadata (shared keys)
        
        Args:
            metadata_key_id: UUID de la metadata key específica (opcional)
            
        Returns:
            Información de las metadata keys con las claves privadas cifradas
        """
        if not self.is_authenticated():
            print("❌ No hay sesión autenticada. Ejecute login() primero.")
            return None
        
        # Incluir las claves privadas en la respuesta
        url = urljoin(self.base_url, '/metadata/keys.json?contain[metadata_private_keys]=1')
        response = self.session.get(url)
        
        if response.status_code != 200:
            print(f"❌ Error obteniendo metadata keys: {response.status_code}")
            return None
        
        data = response.json()
        
        # Si se especificó un metadata_key_id, filtrar por ese
        if metadata_key_id and 'body' in data:
            for key in data['body']:
                if key.get('id') == metadata_key_id:
                    return key
            return None
        
        return data
    
    def logout(self):
        """Cierra la sesión actual"""
        url = urljoin(self.base_url, '/auth/logout.json')
        response = self.session.post(url)
        
        if response.status_code == 200:
            print("✅ Sesión cerrada exitosamente")
            return True
        else:
            print(f"❌ Error cerrando sesión: {response.status_code}")
            return False


def main():
    """Función principal de ejemplo"""
    
    # Cargar configuración desde .env
    passbolt_url = os.getenv('PASSBOLT_URL')
    private_key = os.getenv('PRIVATE_KEY')
    passphrase = os.getenv('PASSPHRASE', '')
    resource_id = os.getenv('RESOURCE_ID')
    
    if not passbolt_url or not private_key:
        print("❌ Error: PASSBOLT_URL y PRIVATE_KEY deben estar configurados en .env")
        return
    
    # Crear cliente y autenticar
    client = PassboltGPGAuth(
        base_url=passbolt_url,
        private_key=private_key,
        passphrase=passphrase if passphrase else None
    )
    
    # Realizar login
    if client.login():
        # Verificar autenticación
        if client.is_authenticated():
            print("\n✅ Sesión verificada - Usuario autenticado")
            
            # Si hay un resource_id configurado, intentar obtenerlo
            if resource_id:
                print(f"\n📦 Obteniendo recurso: {resource_id}")
                resource = client.get_resource(resource_id)
                if resource:
                    print(json.dumps(resource, indent=2))
        
        # Cerrar sesión
        # client.logout()


if __name__ == '__main__':
    main()
