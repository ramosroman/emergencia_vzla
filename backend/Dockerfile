FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para asyncpg y Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY app/ /app/app/

# Puerto de la aplicación
EXPOSE 8000

# Comando de inicio con Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
