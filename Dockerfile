FROM python:3.11-slim

# Evitar que Python escriba archivos .pyc en el disco
ENV PYTHONDONTWRITEBYTECODE=1

# Evitar que Python almacene en búfer stdout y stderr
ENV PYTHONUNBUFFERED=1

# Puerto por defecto (se puede sobreescribir por entorno, e.g. en Railway/Render)
ENV PORT=8000

WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . .

# Exponer el puerto
EXPOSE 8000

# Comando para iniciar la aplicación usando uvicorn.
# Nota: se usa 'sh -c' para expandir la variable de entorno $PORT dinámicamente.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
