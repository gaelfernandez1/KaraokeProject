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

# faster-whisper 1.0.1 hard-pins av==11.*, and PyAV 11 ships no wheel for
# cp310, so pip must build it from source. PyAV 11 also needs FFmpeg >= 5
# (AV_CODEC_CAP_OTHER_THREADS), but Ubuntu 22.04's apt only has 4.4 and the
# pytorch base env carries FFmpeg 4.3 — both too old. So pull FFmpeg 6 from
# conda-forge (with the libmamba solver; the classic solver never finishes in
# this constrained env) and build av against it. Only the native FFmpeg libs
# come from conda — av itself stays pip-managed like the rest of the stack.
RUN conda install -c conda-forge --solver=libmamba "ffmpeg=6" -y && conda clean -a -y
RUN PKG_CONFIG_PATH=/opt/conda/lib/pkgconfig \
    pip install --no-cache-dir "av==11.*"

# openai-whisper uses a legacy setup.py that imports pkg_resources, which is
# unavailable inside pip's isolated build env; install it first without isolation
RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20231117
RUN pip install --no-cache-dir -e ".[whisperx]"

COPY . /KaraokeProject

RUN mkdir -p /data

EXPOSE 5001
CMD ["python", "-m", "whisperx_service.api"]
