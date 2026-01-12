# Passbolt CLI - Cliente para API v5

Una solución completa en Python para descargar y gestionar recursos (credenciales) desde Passbolt v5 utilizando la API REST con autenticación GPGAuth.

## 📋 Descripción

Este proyecto proporciona una interfaz de línea de comandos (CLI) para interactuar con Passbolt v5, permitiendo:

- **Listar recursos**: Visualizar todos los recursos disponibles con filtros de búsqueda
- **Descargar recursos**: Obtener credenciales específicas con descifrado automático
- **Exportar formatos**: Guardar en JSON o formato `.env` para integración en aplicaciones
- **Soporte completo v5**: Compatible con el nuevo formato de metadata cifrado de Passbolt v5

## 🚀 Características

✅ Autenticación segura mediante GPGAuth (protocolo basado en cookies)  
✅ Descifrado automático de secretos y metadata  
✅ Soporte para recursos v5 de Passbolt  
✅ Exportación a múltiples formatos (JSON, .env)  
✅ Interfaz CLI intuitiva con búsqueda y filtros  
✅ Containerizado con Docker para portabilidad  
✅ Sin dependencias del cliente oficial de Passbolt

## 📦 Requisitos

### Opción 1: Docker (Recomendado)
- Docker instalado en tu sistema

### Opción 2: Instalación Local
- Python 3.11 o superior
- GnuPG instalado en el sistema
- pip para gestión de dependencias

## 🔧 Instalación

### Usando Docker

1. **Construir la imagen**:
```bash
docker build -t passbolt-cli .
```

2. **Crear archivo `.env`** con tus credenciales:
```env
PASSBOLT_URL=https://tu-instancia.passbolt.com
PRIVATE_KEY=-----BEGIN PGP PRIVATE KEY BLOCK-----
...
-----END PGP PRIVATE KEY BLOCK-----
PASSPHRASE=tu-passphrase
```

### Instalación Local

1. **Clonar el repositorio**:
```bash
git clone <tu-repositorio>
cd passbolt_env
```

2. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

3. **Configurar variables de entorno**:
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

## 🎯 Uso

### Con Docker

#### Listar todos los recursos
```bash
docker run --rm --env-file .env passbolt-cli --list
```

#### Buscar recursos específicos
```bash
docker run --rm --env-file .env passbolt-cli --list --search "database"
```

#### Descargar un recurso específico
```bash
docker run --rm -v ${PWD}:/app/out --env-file .env \
  passbolt-cli --download <RESOURCE_ID>
```

#### Exportar a formato .env
```bash
docker run --rm -v ${PWD}:/app/out --env-file .env \
  passbolt-cli --download <RESOURCE_ID> -e
```

#### Exportar a JSON
```bash
docker run --rm -v ${PWD}:/app/out --env-file .env \
  passbolt-cli --download <RESOURCE_ID> -j
```

### Uso Local

#### Listar recursos
```bash
python passbolt_cli.py --list
```

#### Buscar recursos
```bash
python passbolt_cli.py --list --search "produccion"
```

#### Descargar recurso
```bash
python passbolt_cli.py --download <RESOURCE_ID>
```

#### Exportar a .env
```bash
python passbolt_cli.py --download <RESOURCE_ID> -e
```

#### Exportar a JSON
```bash
python passbolt_cli.py --download <RESOURCE_ID> -j
```

### Usando variables de entorno directamente (Docker)

Para mayor seguridad, puedes pasar las credenciales como variables de entorno:

```bash
docker run --rm -v ${PWD}:/app/out \
  -e PASSBOLT_URL="https://passbolt.apps.example.com" \
  -e PRIVATE_KEY="-----BEGIN PGP PRIVATE KEY BLOCK----- ..." \
  -e PASSPHRASE="tu-passphrase" \
  passbolt-cli --download <RESOURCE_ID> -e
```

## 📖 Argumentos de CLI

| Argumento | Descripción | Ejemplo |
|-----------|-------------|---------|
| `--list` | Lista todos los recursos disponibles | `--list` |
| `--search <término>` | Filtra recursos por término de búsqueda | `--search database` |
| `--limit <número>` | Limita el número de resultados (default: 20) | `--limit 50` |
| `--download <ID>` | Descarga un recurso específico por ID | `--download bd54ca48-...` |
| `-j, --json` | Exporta el recurso descargado a JSON | `-j` |
| `-e, --env` | Exporta el recurso a formato .env | `-e` |

## 🔐 Configuración de Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
# URL de tu instancia de Passbolt
PASSBOLT_URL=https://passbolt.apps.example.com

# Tu clave privada PGP (incluye BEGIN y END)
PRIVATE_KEY=-----BEGIN PGP PRIVATE KEY BLOCK-----
xYYEaRTeoRYJKwYBBAHaRw8BAQdAzIrjEhJK...
...
=StWT
-----END PGP PRIVATE KEY BLOCK-----

# Passphrase para descifrar tu clave privada
PASSPHRASE=tu-passphrase-seguro

# (Opcional) ID de recurso por defecto
RESOURCE_ID=bd54ca48-d830-4181-ae4f-abab3006985d
```

### Obtener tu clave privada PGP

1. Accede a tu cuenta en Passbolt (web)
2. Ve a **Perfil** → **Claves** → **Clave Privada**
3. Copia el contenido completo (incluyendo BEGIN y END)
4. Pégalo en la variable `PRIVATE_KEY`

## 🏗️ Arquitectura

### Componentes Principales

1. **passbolt_cli.py**: Interfaz de línea de comandos
   - Maneja argumentos del usuario
   - Coordina operaciones de listado y descarga
   - Gestiona exportación a diferentes formatos

2. **passbolt_fetch_resource.py**: Cliente API de Passbolt
   - Implementa autenticación GPGAuth
   - Gestiona cifrado/descifrado PGP
   - Realiza peticiones HTTP a la API

3. **Dockerfile**: Containerización
   - Imagen base Python 3.11
   - Incluye GnuPG para operaciones criptográficas
   - Volumen montado para salida de archivos

### Flujo de Autenticación (GPGAuth)

```
┌─────────────┐                    ┌─────────────┐
│   Cliente   │                    │  Servidor   │
│  (Script)   │                    │  Passbolt   │
└──────┬──────┘                    └──────┬──────┘
       │                                  │
       │  1. GET /auth/verify.json        │
       ├─────────────────────────────────>│
       │  (Obtener clave pública)         │
       │<─────────────────────────────────┤
       │                                  │
       │  2. POST /auth/login.json        │
       │     {keyid: fingerprint}         │
       ├─────────────────────────────────>│
       │  (Solicitar challenge)           │
       │<─────────────────────────────────┤
       │  X-GPGAuth-User-Auth-Token       │
       │  (Token cifrado)                 │
       │                                  │
       │  3. Descifrar token con clave    │
       │     privada local                │
       │                                  │
       │  4. POST /auth/login.json        │
       │     {user_token_result: token}   │
       ├─────────────────────────────────>│
       │  (Enviar token descifrado)       │
       │<─────────────────────────────────┤
       │  Set-Cookie: csrfToken           │
       │  ✓ Autenticado                   │
       │                                  │
       │  5. Requests con cookie          │
       ├─────────────────────────────────>│
       │                                  │
```

## 🔍 Formatos de Salida

### Salida de Consola
```
==================================================================
INFORMACIÓN DEL RECURSO
==================================================================
ID:          bd54ca48-d830-4181-ae4f-abab3006985d
Nombre:      Database Production
Username:    admin
URI:         https://db.example.com
Description: Credenciales de producción
==================================================================

→ Descifrando secreto...
✓ Secreto descifrado correctamente

==================================================================
SECRETO DESCIFRADO
==================================================================
{
    "password": "super-secret-password-123",
    "description": "Credenciales de acceso a la BD"
}
==================================================================
```

### Formato .env
```env
# Recurso: Database Production
# ID: bd54ca48-d830-4181-ae4f-abab3006985d
# Descargado: 2026-01-12 10:30:45

USERNAME=admin
PASSWORD=super-secret-password-123
URI=https://db.example.com
DESCRIPTION=Credenciales de producción
```

### Formato JSON
```json
{
    "resource_id": "bd54ca48-d830-4181-ae4f-abab3006985d",
    "name": "Database Production",
    "username": "admin",
    "uri": "https://db.example.com",
    "description": "Credenciales de producción",
    "secret": {
        "password": "super-secret-password-123",
        "description": "Credenciales de acceso a la BD"
    },
    "metadata": {
        "resource_type_id": "669f8c64-242a-59fb-92e5-...",
        "created": "2024-05-22T10:15:30+00:00",
        "modified": "2024-05-22T10:15:30+00:00"
    },
    "downloaded_at": "2026-01-12T10:30:45.123456"
}
```

## 🛠️ Desarrollo

### Estructura del Proyecto
```
passbolt_env/
├── passbolt_cli.py              # CLI principal
├── passbolt_fetch_resource.py   # Cliente API
├── Dockerfile                    # Imagen Docker
├── requirements.txt              # Dependencias Python
├── .env.example                  # Template de configuración
├── README.md                     # Este archivo
├── README_DOCKER.md             # Guía de Docker
└── doc_passbolt.yaml            # Especificación OpenAPI
```

### Dependencias

- **requests**: Cliente HTTP para llamadas a la API
- **python-gnupg**: Wrapper de GnuPG para operaciones criptográficas
- **python-dotenv**: Gestión de variables de entorno

### Ejecutar Tests
```bash
# Verificar conexión
python passbolt_cli.py --list --limit 1

# Test de descarga
python passbolt_cli.py --download <RESOURCE_ID>
```

## 🐛 Solución de Problemas

### Error: "No se pudo importar la clave privada PGP"
- Verifica que la clave incluya `-----BEGIN PGP PRIVATE KEY BLOCK-----` y `-----END PGP PRIVATE KEY BLOCK-----`
- Asegúrate de que no haya espacios o caracteres extra al inicio/final

### Error: "El servidor no devolvió el token de autenticación"
- Verifica que `PASSBOLT_URL` sea correcta (sin `/` al final)
- Confirma que tu clave PGP esté registrada en el servidor Passbolt

### Error: "Failed to decrypt"
- Verifica que `PASSPHRASE` sea correcta
- Confirma que la clave privada corresponda a la clave pública registrada en Passbolt

### Problemas con Docker en Windows (PowerShell)
- Usa `${PWD}` en lugar de `$(pwd)` para rutas
- Asegúrate de que Docker Desktop esté ejecutándose

## 📝 Ejemplos de Integración

### CI/CD Pipeline (GitHub Actions)
```yaml
- name: Download Passbolt Secret
  run: |
    docker run --rm -v ${{ github.workspace }}:/app/out \
      -e PASSBOLT_URL="${{ secrets.PASSBOLT_URL }}" \
      -e PRIVATE_KEY="${{ secrets.PASSBOLT_PRIVATE_KEY }}" \
      -e PASSPHRASE="${{ secrets.PASSBOLT_PASSPHRASE }}" \
      passbolt-cli --download ${{ secrets.RESOURCE_ID }} -e
    source .env
```

### Script de Deploy
```bash
#!/bin/bash
# deploy.sh

# Descargar credenciales de producción
docker run --rm -v $(pwd):/app/out --env-file .env.passbolt \
  passbolt-cli --download $PROD_CREDENTIALS_ID -e

# Cargar variables
source .env

# Desplegar aplicación con credenciales
docker-compose up -d
```

## 🔒 Seguridad

- ⚠️ **Nunca** commitees el archivo `.env` con credenciales reales
- ✅ Usa `.env.example` como plantilla sin datos sensibles
- ✅ Las claves PGP privadas deben mantenerse seguras
- ✅ Utiliza secretos de CI/CD para entornos automatizados
- ✅ Los archivos exportados (.env, .json) contienen credenciales sensibles

## 📄 Licencia

Este proyecto está bajo licencia MIT. Ver archivo `LICENSE` para más detalles.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 👥 Autor

Desarrollado para facilitar la integración con Passbolt v5 y automatización de gestión de credenciales.

## 📞 Soporte

Para reportar problemas o solicitar features, abre un issue en el repositorio.

---

**Nota**: Este cliente es compatible con Passbolt v5 y utiliza el protocolo GPGAuth legado (cookie-based). Para versiones futuras de Passbolt, verifica la compatibilidad de la API.
