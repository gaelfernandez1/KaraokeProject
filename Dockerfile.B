# O dockerfile para a parte de whisperx. Actualizado con dependencias fijas. Teño documentado o por qué de cada versión, por se fose necesario para a memoria
FROM pytorch/pytorch:2.3.0-cuda11.8-cudnn8-devel

ENV DEBIAN_FRONTEND=noninteractive
#arreglar problemas con variables de entorno intel mkl, polo tema de haber arreglado o de av.
ENV MKL_SERVICE_FORCE_INTEL=1
ENV MKL_THREADING_LAYER=INTEL
ENV OMP_NUM_THREADS=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    build-essential \
    pkg-config \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Ubuntu 20.04 ships ffmpeg 4.2; av==11.* needs AV_CODEC_CAP_OTHER_THREADS (added in 4.4).
# The savoury1 PPA provides 4.4+ for Focal, same as Dockerfile.A.
RUN add-apt-repository ppa:savoury1/ffmpeg4 -y || true && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libavformat-dev \
        libavcodec-dev \
        libavdevice-dev \
        libavutil-dev \
        libavfilter-dev \
        libswscale-dev \
        libswresample-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /KaraokeProject

#versions compatibles en teoria
RUN pip install --no-cache-dir --upgrade \
    pip==24.0 \
    setuptools==69.5.1 \
    wheel==0.43.0

COPY pyproject.toml /KaraokeProject/
COPY src/ /KaraokeProject/src/
# openai-whisper uses a legacy setup.py that imports pkg_resources, which is
# unavailable inside pip's isolated build env; install it first without isolation
RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20231117
RUN pip install --no-cache-dir -e ".[whisperx]"

COPY . /KaraokeProject

RUN mkdir -p /data

EXPOSE 5001
CMD ["python", "-m", "whisperx_service.api"]