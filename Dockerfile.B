# O dockerfile para a parte de whisperx. Actualizado con imagen máis moderna. Teño documentado o por qué de cada versión, por se fose necesario para a memoria
FROM pytorch/pytorch:2.3.0-cuda11.8-cudnn8-devel

ENV DEBIAN_FRONTEND=noninteractive
#arreglar problemas con variables de entorno intel mkl, polo tema de haber arreglado o de av.
ENV MKL_SERVICE_FORCE_INTEL=1
ENV MKL_THREADING_LAYER=INTEL
ENV OMP_NUM_THREADS=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    wget \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /KaraokeProject

#instalar as dependencias paso a paso para evitar os problemas co build
RUN pip install --upgrade pip wheel setuptools

#versions compatibles en teoria
RUN pip install --no-cache-dir \
    torch==2.3.0 \
    torchaudio==2.3.0 \
    torchvision==0.18.0


RUN pip install --no-cache-dir \
    librosa>=0.10.0 \
    soundfile>=0.12.1 \
    scipy>=1.10.0

RUN pip install --no-cache-dir \
    faster-whisper==1.0.1 \
    whisperx==3.1.3


RUN pip install --no-cache-dir \
    Flask>=2.3.0 \
    pyphen>=0.14.0 \
    "numpy<2.0" \
    requests>=2.28.0

COPY whisperx_service_api.py /KaraokeProject/
COPY gpu_utils.py /KaraokeProject/

RUN mkdir -p /data

EXPOSE 5001
CMD ["python", "whisperx_service_api.py"]