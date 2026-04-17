# Passbolt-dwn - Cliente Docker

Cliente de línea de comandos para interactuar con Passbolt desde Docker. Permite listar y descargar recursos utilizando autenticación GPG.

## Requisitos Previos

- Docker instalado
- Clave GPG privada configurada en Passbolt
- Acceso a una instancia de Passbolt

## Configuración

1. **Copia el archivo de ejemplo de configuración:**
   ```bash
   cp .env.example .env
   ```

2. **Edita el archivo .env con tus credenciales:**
   - `PASSBOLT_URL`: URL de tu instancia de Passbolt
   - `PRIVATE_KEY`: Tu clave privada GPG completa
   - `PASSPHRASE`: Passphrase de tu clave GPG
   - `RESOURCE_ID`: (Opcional) ID del recurso por defecto

## Construcción de la Imagen

```bash
docker build -t passbolt-dwn .
```

## Uso

### 1. Listar Recursos

Lista todos los recursos disponibles en Passbolt:

```bash
 docker run --rm -v ${PWD}/out:/app/out -v ${PWD}/private.key:/app/private.key --env-file .env passbolt-dwn --list
```

**Salida:**
- Lista en consola con ID, nombre y URI de cada recurso
- Archivo `out/resources_list.json` con la lista completa

### 2. Descargar Recurso

#### Formato JSON:
```bash
 docker run --rm -v ${PWD}/out:/app/out -v ${PWD}/private.key:/app/private.key --env-file .env passbolt-dwn --download RESOURCE_ID -j
```

**Salida:**
- Archivo `out/resource_RESOURCE_ID.json` con todos los campos

#### Formato ENV:
```bash
docker run --rm -v ${PWD}/out:/app/out -v ${PWD}/private.key:/app/private.key --env-file .env passbolt-dwn --download RESOURCE_ID -e
```

**Salida:**
- Archivo `out/resource_RESOURCE_ID.env` listo para usar con `source` o `docker --env-file`

#### Ambos Formatos:
```bash
docker run --rm -v ${PWD}/out:/app/out -v ${PWD}/private.key:/app/private.key --env-file .env passbolt-dwn --download RESOURCE_ID  -j -e
```

**Salida:**
- Ambos archivos: `.json` y `.env`

## Estructura de Archivos de Salida

### JSON Format (`resource_ID.json`)
```json
{
  "campo1": "valor1",
  "campo2": "valor2",
  "_resource_name": "Nombre del Recurso",
  "_resource_id": "uuid-del-recurso",
  "_resource_uri": "https://ejemplo.com"
}
```

### ENV Format (`resource_ID.env`)
```bash
# Variables del recurso: Nombre del Recurso
# Resource ID: uuid-del-recurso
# Descargado: https://ejemplo.com

campo1="valor1"
campo2="valor2"
```

## Ejemplos Completos

### Workflow Típico


1. **Listar recursos para encontrar el ID:**
   ```bash
   docker run --rm -v ${PWD}/out:/app/out -v ${PWD}/private.key:/app/private.key --env-file .env passbolt-dwn --list
   ```

2. **Descargar recurso específico:**
   ```bash
  docker run --rm -v ${PWD}/out:/app/out -v ${PWD}/private.key:/app/private.key --env-file .env passbolt-dwn --download 6aea0e9e-d76f-493f-81eb-d7df370df425 -e
   ```

3. **Usar las variables:**
   ```bash
   source out/resource_abc123-def456-ghi789.env
   echo $campo1
   ```


## Seguridad

- Los archivos de salida contienen información sensible
- Asegúrate de que el directorio `out/` tenga permisos restringidos
- No commitees el archivo `.env` al control de versiones
- Considera usar Docker secrets en producción

## Solución de Problemas

### Error de autenticación GPG
- Verifica que la clave privada esté completa en `PRIVATE_KEY`
- Asegúrate de que el passphrase sea correcto
- Confirma que la clave esté importada en tu cuenta de Passbolt

### Error de conexión
- Verifica que `PASSBOLT_URL` sea accesible
- Revisa si necesitas configurar certificados SSL
- Comprueba conectividad de red

### Recurso no encontrado
- Usa `--list` para verificar que el recurso existe
- Confirma que tienes permisos para acceder al recurso
- Verifica que el RESOURCE_ID sea correcto

## Ayuda

```bash
docker run --rm passbolt-dwn --help
```