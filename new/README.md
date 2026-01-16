# Passbolt GPGAuth Client - API v5

Cliente Python para autenticación GPGAuth con Passbolt API v5.

## 📋 Requisitos

- Python 3.7+
- GPG (GnuPG) instalado en el sistema
- Acceso a un servidor Passbolt

### Verificar instalación de GPG

```bash
gpg --version
```

## 🔧 Instalación

1. **Instalar dependencias Python:**

```bash
pip install -r requirements.txt
```

2. **Configurar variables de entorno:**

Edita el archivo `.env` con tus credenciales:

```env
PASSBOLT_URL=https://tu-servidor-passbolt.com
RESOURCE_ID=tu-resource-uuid
PRIVATE_KEY='-----BEGIN PGP PRIVATE KEY BLOCK-----
...
-----END PGP PRIVATE KEY BLOCK-----'
PASSPHRASE=tu-passphrase
```

## 🚀 Uso

### Autenticación básica

```python
from passbolt_gpgauth import PassboltGPGAuth
import os

# Crear cliente
client = PassboltGPGAuth(
    base_url=os.getenv('PASSBOLT_URL'),
    private_key=os.getenv('PRIVATE_KEY'),
    passphrase=os.getenv('PASSPHRASE')
)

# Realizar login
if client.login():
    print("✅ Autenticación exitosa")
    
    # Verificar sesión
    if client.is_authenticated():
        print("✅ Sesión activa")
```

### Ejecutar script de ejemplo

```bash
python passbolt_gpgauth.py
```

## 🔐 Flujo de Autenticación GPGAuth

El protocolo GPGAuth implementado sigue estos pasos:

### Paso 1: Verificar Servidor (Stage 0)
```
GET /auth/verify.json
```
- Obtiene la clave pública del servidor
- Importa la clave al keyring GPG local

### Paso 2: Verificación del Usuario (Stage 1)
```
POST /auth/verify.json
{
  "data": {
    "gpg_auth": {
      "keyid": "USER_FINGERPRINT"
    }
  }
}
```
- El servidor cifra un token con nuestra clave pública
- Desciframos el token para demostrar que tenemos la clave privada

### Paso 3: Login Final (Stage 2)
```
POST /auth/login.json
{
  "data": {
    "gpg_auth": {
      "keyid": "USER_FINGERPRINT",
      "user_token_result": "DECRYPTED_TOKEN"
    }
  }
}
```
- Enviamos el token descifrado
- El servidor establece una sesión y devuelve cookies

## 📚 Métodos Disponibles

### `PassboltGPGAuth`

- **`login()`**: Ejecuta el flujo completo de autenticación
- **`is_authenticated()`**: Verifica si la sesión está activa
- **`get_resource(resource_id)`**: Obtiene un recurso/contraseña
- **`logout()`**: Cierra la sesión actual

## 🔍 Ejemplo Completo

```python
import os
from dotenv import load_dotenv
from passbolt_gpgauth import PassboltGPGAuth

load_dotenv()

# Configurar cliente
client = PassboltGPGAuth(
    base_url=os.getenv('PASSBOLT_URL'),
    private_key=os.getenv('PRIVATE_KEY'),
    passphrase=os.getenv('PASSPHRASE')
)

# Autenticar
if client.login():
    # Obtener recurso
    resource_id = os.getenv('RESOURCE_ID')
    resource = client.get_resource(resource_id)
    
    if resource:
        print(f"Recurso: {resource['body']['name']}")
        print(f"Username: {resource['body']['username']}")
    
    # Cerrar sesión
    client.logout()
```

## 🛠️ Troubleshooting

### Error: "gpg: decryption failed: No secret key"

Verifica que tu clave privada esté correctamente formateada en `.env` y que la passphrase sea correcta.

### Error: "Error al importar clave privada"

Asegúrate de que GPG esté instalado:
```bash
# Windows (con Chocolatey)
choco install gpg4win

# Linux
sudo apt-get install gnupg

# macOS
brew install gnupg
```

### Error de conexión SSL

Si el servidor usa un certificado autofirmado:
```python
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# En las peticiones
response = self.session.get(url, verify=False)
```

## 📖 Documentación API

Este cliente implementa el protocolo descrito en `passbolt.yml` (OpenAPI 3.1.0).

Endpoints principales:
- `GET /auth/verify.json` - Obtener clave pública del servidor
- `POST /auth/verify.json` - Verificar identidad mutua
- `POST /auth/login.json` - Completar login
- `GET /auth/is-authenticated.json` - Verificar sesión
- `POST /auth/logout.json` - Cerrar sesión
- `GET /resources/{id}.json` - Obtener recurso

## 🔒 Seguridad

- ⚠️ **NUNCA** subas el archivo `.env` a Git
- Las claves privadas se importan temporalmente al keyring GPG
- Las passphrases se manejan en memoria
- Las sesiones usan cookies seguras

## 📝 Notas

- Compatible con Passbolt API v5
- Requiere GPG 2.x o superior
- Soporta claves RSA y ECC
- Las cookies de sesión se mantienen en `requests.Session()`

## 🤝 Contribuciones

Para reportar issues o contribuir, consulta la documentación de Passbolt:
- https://www.passbolt.com/docs/api/
- https://help.passbolt.com/api

## 📄 Licencia

Este código es proporcionado como ejemplo educativo.
