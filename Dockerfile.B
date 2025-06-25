# O dockerfile para a parte de whisperx. Teño documentado o por qué de cada versión, por se fose necesario para a memoria.

FROM pytorch/pytorch:2.0.0-cuda11.7-cudnn8-devel

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /KaraokeProject

COPY requirementsB.txt /KaraokeProject/
RUN pip install --no-cache-dir -r requirementsB.txt

COPY whisperx_service_api.py /KaraokeProject/
COPY gpu_utils.py /KaraokeProject/

RUN mkdir -p /data

EXPOSE 5001
CMD ["python", "whisperx_service_api.py"]