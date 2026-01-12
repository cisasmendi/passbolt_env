FROM python:3.11-slim

WORKDIR /app

# Instalar GPG (requerido por python-gnupg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gnupg && \
    rm -rf /var/lib/apt/lists/*

# Copiar archivos de requisitos e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar scripts de la aplicación
COPY passbolt_cli.py .
COPY passbolt_fetch_resource.py .

# Crear directorio de salida
RUN mkdir -p out

# Configurar volumen para archivos de salida
VOLUME ["/app/out"]

# Punto de entrada
ENTRYPOINT ["python", "passbolt_cli.py"]

# Comando por defecto (mostrar ayuda)
CMD ["--help"]
