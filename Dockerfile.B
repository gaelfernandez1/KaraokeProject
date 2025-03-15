# Dockerfile.whisperx

FROM pytorch/pytorch:2.0.0-cuda11.7-cudnn8-devel

# ffmpeg, git, etc.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /KaraokeProject

# Instalar requirements B
COPY requirementsB.txt /KaraokeProject
RUN pip install --no-cache-dir -r requirementsB.txt

# Copiar whisperx_service_api.py
COPY whisperx_service_api.py /KaraokeProject

EXPOSE 5001
CMD ["python", "whisperx_service_api.py"]
