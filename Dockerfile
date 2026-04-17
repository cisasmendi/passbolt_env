FROM python:3.11-slim

WORKDIR /app

# Instalar GPG (requerido por python-gnupg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gnupg && \
    rm -rf /var/lib/apt/lists/*

# Copiar archivos de requisitos e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY *.py .

# Crear directorio de salida
RUN mkdir -p /app/out

# Hacer el script principal ejecutable
RUN chmod +x main.py

# Punto de entrada
ENTRYPOINT ["python", "main.py"]


