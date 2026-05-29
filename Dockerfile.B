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

# av==11.* (required by faster-whisper) has no pre-built pip wheel for this
# conda-based Python environment and needs ffmpeg >= 4.4 headers to compile.
# The apt ffmpeg on Ubuntu 20.04 is 4.2. Install ffmpeg from conda-forge
# (which lands at /opt/conda) and build av against those headers explicitly.
RUN conda install -c conda-forge ffmpeg cython -y && conda clean -a -y
RUN PKG_CONFIG_PATH=/opt/conda/lib/pkgconfig \
    pip install --no-cache-dir --no-build-isolation "av==11.*"

# openai-whisper uses a legacy setup.py that imports pkg_resources, which is
# unavailable inside pip's isolated build env; install it first without isolation
RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20231117
RUN pip install --no-cache-dir -e ".[whisperx]"

COPY . /KaraokeProject

RUN mkdir -p /data

EXPOSE 5001
CMD ["python", "-m", "whisperx_service.api"]
