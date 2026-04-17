import requests
import gnupg
import json
import os
import urllib3
from config import config

# Desactivar warnings de SSL si es necesario
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

config.validate()

PASSBOLT_URL = config.passbolt_url
RESOURCE_ID = config.resource_id
GPG_PRIVATE_KEY = config.private_key
GPG_PASSPHRASE = config.passphrase

GPG_HOME = "./.gnupg"

# 1. Inicializar GPG
os.makedirs(GPG_HOME, exist_ok=True)
gpg = gnupg.GPG(gnupghome=GPG_HOME)

# 2. Importar clave desde string
import_result = gpg.import_keys(GPG_PRIVATE_KEY)

if not import_result.count:
    print("stderr:", import_result.stderr)
    print("results:", import_result.results)
    raise Exception("No se pudo importar la clave GPG")

fingerprint = import_result.fingerprints[0]
print(f"Clave importada: {fingerprint}")

# 3. GPGAuth - Login (protocolo challenge-response)
session = requests.Session()
session.verify = False  # Cambiar a True si el cert SSL es válido

# Paso 1: Enviar fingerprint, el servidor responde con un token cifrado
print("\n[GPGAuth] Paso 1: Solicitando challenge...")
resp = session.post(
    f"{PASSBOLT_URL}/auth/login.json",
    json={"data": {"gpg_auth": {"keyid": fingerprint}}}
)

# El token cifrado viene en el header X-GPGAuth-User-Auth-Token
encrypted_token = resp.headers.get("X-GPGAuth-User-Auth-Token")
if not encrypted_token:
    print("Headers:", dict(resp.headers))
    print("Body:", resp.text)
    raise Exception("No se recibió X-GPGAuth-User-Auth-Token del servidor")

# URL-decode del token (viene URL-encoded)
encrypted_token = requests.utils.unquote(encrypted_token)
encrypted_token = encrypted_token.replace("\\+", " ")

# Paso 2: Descifrar el token con nuestra clave privada
print("[GPGAuth] Paso 2: Descifrando challenge...")
decrypted = gpg.decrypt(encrypted_token, passphrase=GPG_PASSPHRASE)
if not decrypted.ok:
    raise Exception(f"Error descifrando token GPGAuth: {decrypted.status}")

user_token_result = str(decrypted)
print(f"[GPGAuth] Token descifrado: {user_token_result}")

# Paso 3: Enviar el token descifrado para completar login
print("[GPGAuth] Paso 3: Completando login...")
resp = session.post(
    f"{PASSBOLT_URL}/auth/login.json",
    json={"data": {"gpg_auth": {"keyid": fingerprint, "user_token_result": user_token_result}}}
)

if resp.status_code != 200:
    print("Status:", resp.status_code)
    print("Body:", resp.text)
    raise Exception("Falló el login GPGAuth")

print("[GPGAuth] Login exitoso!")

# 4. Obtener metadatos del recurso
print(f"\nObteniendo recurso {RESOURCE_ID}...")
resp = session.get(f"{PASSBOLT_URL}/resources/{RESOURCE_ID}.json")
resp.raise_for_status()
resource = resp.json()["body"]

# Descifrar metadata (contiene los nombres de los campos personalizados)
encrypted_metadata = resource.get("metadata", "")
field_names_map = {}
if encrypted_metadata.startswith("-----BEGIN PGP MESSAGE-----"):
    print("Descifrando metadata...")
    dec_meta = gpg.decrypt(encrypted_metadata, passphrase=GPG_PASSPHRASE)
    if dec_meta.ok:
        metadata = json.loads(str(dec_meta))
        print(f"[DEBUG] Metadata descifrada: {json.dumps(metadata, indent=2)}")
        # Mapear IDs de campos a sus nombres
        for cf in metadata.get("custom_fields", []):
            field_names_map[cf["id"]] = cf.get("metadata_key", cf.get("label", cf.get("name", cf["id"])))
    else:
        print(f"[WARN] No se pudo descifrar metadata: {dec_meta.status}")

# 5. Obtener secreto del recurso
print(f"Obteniendo secreto...")
resp = session.get(f"{PASSBOLT_URL}/secrets/resource/{RESOURCE_ID}.json")
resp.raise_for_status()

secret_body = resp.json()["body"]
encrypted_secret = secret_body["data"] if isinstance(secret_body, dict) else secret_body

# 6. Desencriptar el secreto
decrypted = gpg.decrypt(encrypted_secret, passphrase=GPG_PASSPHRASE)

if not decrypted.ok:
    raise Exception(f"Error GPG al descifrar secreto: {decrypted.status}")

# 7. Parsear JSON (custom fields)
data = json.loads(str(decrypted))

# 8. Cruzar nombres de metadata con valores del secreto
custom_fields = data.get("custom_fields", [])
result = {}

if isinstance(custom_fields, list):
    for field in custom_fields:
        field_id = field.get("id", "")
        value = field.get("secret_value", field.get("value", ""))
        label = field_names_map.get(field_id, field_id)
        result[label] = str(value)
else:
    for key, value in data.items():
        if key != "object_type":
            result[key] = str(value)

# 9. Mostrar resultados
print("\n=== VARIABLES (Campos Personalizados) ===\n")
for key, value in result.items():
    os.environ[key] = value
    print(f"{key}={value}")

# 10. Guardar en out.json
with open("out.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
print("\nGuardado en out.json")

# 11. Guardar en .env.example
with open(".env.example_out", "w", encoding="utf-8") as f:
    f.write("# Variables obtenidas de Passbolt\n")
    for key, value in result.items():
        f.write(f"{key}={value}\n")
print("Guardado en .env.example_out")