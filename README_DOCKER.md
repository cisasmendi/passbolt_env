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
docker run --rm -v ${PWD}:/app/out -e PASSBOLT_URL="https://passbolt.apps.cc.gob.ar" -e PRIVATE_KEY="-----BEGIN PGP PRIVATE KEY BLOCK-----

xYYEaRTeoRYJKwYBBAHaRw8BAQdAzIrjEhJK6NgNAiqyKv87fTNGpWhbKKy6
ahCEFcaK54/+CQMIVJDL9XREToHgAAAAAAAAAAAAAAAAAAAAACj7NV6K8/2X
vjiBdi8AJed40ivkEcYyn1NaKm3f3VvY8523Vsu81xfObbCh8uQcVx8JXY4l
Ws0pY2FybG9zIGlzYXNtZW5kaSA8Y2lzYXNtZW5kaUB1bmNhLmVkdS5hcj7C
wBMEExYKAIUFgmkU3qEDCwkHCZArqwGLHGkI/UUUAAAAAAAcACBzYWx0QG5v
dGF0aW9ucy5vcGVucGdwanMub3Jna4ti8b/35ZMgP2zktBSGpPOa/UCSO6fJ
xJFTeoPkBdMFFQoIDgwEFgACAQIZAQKbAwIeARYhBKCOVeydDqG/qm1aBCur
AYscaQj9AACldgEAuCZLD8OJH33Rnk2SLTEvKDEbn2TUI7309r6m7F8xj8YB
AOQEL6W/OeqjRJ6bxeoxUCOs1B2x9wTU/ijnMImOPr4Fx4sEaRTeoRIKKwYB
BAGXVQEFAQEHQEsGlk5FsIBsctmb6AJTnTHsexVG7+ul9VN/Cbj10t0oAwEI
B/4JAwjlkKh+uS2dAeAAAAAAAAAAAAAAAAAAAAAAW2v5JQ9vooUSTKAyjYPp
k8lBIzN6KSgwZsTHcYbW+7NMeQuSUakGeC/4c1hkBwna+4Pai0bJwr4EGBYK
AHAFgmkU3qEJkCurAYscaQj9RRQAAAAAABwAIHNhbHRAbm90YXRpb25zLm9w
ZW5wZ3Bqcy5vcmcrV3XQ9aNCsF9xsa5RN1w/gp82YjMzgt8/TiXdrHJFagKb
DBYhBKCOVeydDqG/qm1aBCurAYscaQj9AABQjwD+ObomLepilGAQwUl3VCrD
e12D09HjD6ECClagvgb3tIEBAME5ZWFOS0+DCP6nlEjIpS5gpy5HleJje6OD
dUVUxE4F
=StWT
-----END PGP PRIVATE KEY BLOCK-----" -e PASSPHRASE="cis@smendi" passbolt-cli --download bd54ca48-d830-4181-ae4f-abab3006985d -j
```

**Descargar recurso en formato ENV:**
```bash
docker run --rm -v ${PWD}/out:/app/out --env-file .env passbolt-cli --download RESOURCE_ID -e
```

**Descargar en ambos formatos:**
```bash
docker run --rm -v ${PWD}/out:/app/out --env-file .env passbolt-cli --download RESOURCE_ID -j -e
```

### 2. Con Docker Compose

**Descargar en formato JSON (comando por defecto):**
```bash
docker-compose run --rm passbolt-cli
```

**Descargar en formato ENV:**
```bash
docker-compose run --rm passbolt-cli --download --env
```

**Descargar en ambos formatos:**
```bash
docker-compose run --rm passbolt-cli --download -j -e
```

**Listar recursos:**
```bash
docker-compose run --rm passbolt-cli --list
```

**Buscar recursos:**
```bash
docker-compose run --rm passbolt-cli --list --search "password"
```

## Notas importantes

- Los archivos generados aparecerán en el directorio `./out/` del host
- El archivo `.env` debe existir en el directorio actual con las credenciales de Passbolt
- El contenedor se ejecuta con `--rm` para eliminarse automáticamente después de la ejecución


