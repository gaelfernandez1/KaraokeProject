# O dockerfile para a parte de whisperx. Actualizado con dependencias fijas. Teño documentado o por qué de cada versión, por se fose necesario para a memoria
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

#versions compatibles en teoria
RUN pip install --no-cache-dir --upgrade \
    pip==24.0 \
    setuptools==69.5.1 \
    wheel==0.43.0

COPY pyproject.toml /KaraokeProject/
COPY src/ /KaraokeProject/src/
RUN pip install --no-cache-dir -e ".[whisperx]"

COPY . /KaraokeProject

RUN mkdir -p /data

EXPOSE 5001
CMD ["python", "-m", "whisperx_service.api"]