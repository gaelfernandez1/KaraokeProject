# Dockerfile.whisperx

FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg git

WORKDIR /KaraokeProject

# Copiar el requirements de whisperx
COPY requirementsB.txt /KaraokeProject

# Instalar dependencias con pip
RUN pip install --no-cache-dir -r requirementsB.txt

# Copiar el archivo que monta el servidor whisperx (whisperx_service_api.py)
COPY whisperx_service_api.py /KaraokeProject

# Exponer el puerto 5001 (donde correrá el servidor Flask)
EXPOSE 5001

# Comando por defecto: lanzar la API
CMD ["python", "whisperx_service_api.py"]
