# Usa Python 3.10 slim (imágen ligera)
FROM python:3.10-slim

# Crea y usa un directorio /app
WORKDIR /app

# Copia todo el código
COPY . .

# Instala dependencias del sistema: ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Instala dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Expone el puerto interno (no es estrictamente necesario para Heroku, pero sirve de documentación)
EXPOSE 5000

# IMPORTANTE:
# Usa la forma "shell" (sh -c) para que la variable $PORT se expanda correctamente
# OJO: Bajamos a 1 worker para reducir consumo y quizá tardar un poco menos
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT app:app --workers=1 --timeout=90"]
