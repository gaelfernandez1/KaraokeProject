import logging

import requests

logger = logging.getLogger(__name__)


# Esto chama ao endpoint de  whisperx para facer a transcripción automatica
def call_whisperx_endpoint(
    vocals_path: str,
    enable_diarization: bool = False,
    hf_token: str = None,
    whisper_model: str = "small",
):
    url = "http://whisperx:5001/align"  # dentro da rede docker
    datos_envio = {
        "audio_path": vocals_path,
        "enable_diarization": enable_diarization,
        "whisper_model": whisper_model,
    }

    # Agregar token de HuggingFace
    if hf_token:
        datos_envio["hf_token"] = hf_token

    # Facemos post
    try:
        resposta = requests.post(url, json=datos_envio, timeout=600)
        if resposta.status_code == 200:
            datos = resposta.json()
            return datos  # Devolver datos para acceder a speaker_info
        else:
            logger.error(f"WhisperX alignment Error: {resposta.text}")
            return None
    except Exception as e:
        logger.exception(f"error ao chamar ao endpoint: {e}")
        return None


# Esto chama ao endpoint pero da letra manual
def call_whisperx_endpoint_manual(
    vocals_path: str,
    manual_lyrics: str,
    language: str | None = None,
    enable_diarization: bool = False,
    hf_token: str | None = None,
    whisper_model: str = "small",
):
    url = "http://whisperx:5001/align"
    datos_envio = {
        "audio_path": vocals_path,
        "manual_lyrics": manual_lyrics,
        "enable_diarization": enable_diarization,
        "whisper_model": whisper_model,
    }

    # Solo añadir language si se especifica, si non WhisperX detectará automáticamente
    if language:
        datos_envio["language"] = language

    if hf_token:
        datos_envio["hf_token"] = hf_token

    try:
        resposta = requests.post(url, json=datos_envio, timeout=600)
        if resposta.status_code == 200:
            datos = resposta.json()
            return datos
        else:
            logger.error(f"Fallo do alineamento forzado: {resposta.text}")
            return None
    except Exception as e:
        logger.exception(f"error co endpoint da letra manual {e}")
        return None
