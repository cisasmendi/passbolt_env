# Passbolt CLI - Docker

## Construcción de la imagen

```bash
docker build -t passbolt-cli .
```

## Uso

### 1. Con Docker directamente

**Listar recursos:**
```bash
docker run --rm -v ${PWD}/out:/app/out --env-file .env passbolt-cli --list
```

**Descargar recurso en formato JSON:**
```bash
docker run --rm -v ${PWD}/out:/app/out --env-file .env passbolt-cli --download RESOURCE_ID -j
```

**Descargar recurso en formato ENV:**
```bash
docker run --rm -v ${PWD}/out:/app/out --env-file .env passbolt-cli --download RESOURCE_ID -e
```

**Descargar en ambos formatos:**
```bash
docker run --rm -v ${PWD}/out:/app/out --env-file .env passbolt-cli --download RESOURCE_ID -j -e
```
