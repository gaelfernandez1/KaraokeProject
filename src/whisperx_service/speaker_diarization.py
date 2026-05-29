import os
import torch
from pyannote.audio import Pipeline
from pyannote.core import Segment
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def perform_speaker_diarization(audio_path: str, hf_token: str = None):

    try:
        if not os.path.exists(audio_path):
            return None
        
        if not hf_token:
            logger.error("Fai falta o token de hugging face")
            return None
        
        
        try:
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token
            )
            logger.info("Pipeline diarization cargado correctamente")
        except Exception as e:
            return None
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Configurando dispositivo: {device}")
        
        try:
            pipeline = pipeline.to(device)
        except Exception as e:
            return None
        
        logger.info(f"Executando speaker diarization en: {audio_path}")
        
        try:
            diarization = pipeline(audio_path)
        except Exception as e:
            logger.error(f"Error executando diarization: {e}")
            return None
        
        speaker_segments = []
        speakers_found = set()
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speakers_found.add(speaker)
            speaker_segments.append({
                "start": turn.start,
                "end": turn.end,
                "speaker": speaker
            })
        
        logger.info(f"Encontrados {len(speakers_found)} speakers: {list(speakers_found)}")
        
        if len(speakers_found) == 0:
            logger.warning("non se toparon speakers: usando speaker por defecto")
            return {
                "speakers": ["SPEAKER_00"],
                "segments": [{
                    "start": 0.0,
                    "end": 999.0,  
                    "speaker": "SPEAKER_00"
                }],
                "num_speakers": 1
            }
        
        return {
            "speakers": list(speakers_found),
            "segments": speaker_segments,
            "num_speakers": len(speakers_found)
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None



# basase na superposicion temporal
def assign_speaker_to_word(word_segment, speaker_segments):

    word_start = word_segment["start"]
    word_end = word_segment["end"]
    word_center = (word_start + word_end) / 2
    
    #buscar o speakerque mellor se superón
    best_speaker = None
    best_overlap = 0
    
    for speaker_seg in speaker_segments:
        speaker_start = speaker_seg["start"]
        speaker_end = speaker_seg["end"]
        
        # Calcular superposición
        overlap_start = max(word_start, speaker_start)
        overlap_end = min(word_end, speaker_end)
        overlap_duration = max(0, overlap_end - overlap_start)
        
        # Si o centro da palabra está dentro do segmento do speaker
        if speaker_start <= word_center <= speaker_end:
            if overlap_duration > best_overlap:
                best_overlap = overlap_duration
                best_speaker = speaker_seg["speaker"]
    
    return best_speaker

def merge_transcription_with_speakers(word_segments, speaker_segments):

    enriched_segments = []
    
    for word_seg in word_segments:
        speaker = assign_speaker_to_word(word_seg, speaker_segments)
        
        enriched_seg = word_seg.copy()
        enriched_seg["speaker"] = speaker if speaker else "SPEAKER_00"  
        enriched_segments.append(enriched_seg)
    
    return enriched_segments

def get_speaker_colors():

    return [
        "#FF6B6B", 
        "#4ECDC4",  
        "#45B7D1",  
        "#FFA07A",  
        "#98D8C8", 
        "#F7DC6F",  
        "#BB8FCE",  
        "#85C1E9",  
        "#F8C471",  
        "#82E0AA"   
    ]

def assign_colors_to_speakers(speakers):

    colors = get_speaker_colors()
    speaker_colors = {}
    
    for i, speaker in enumerate(speakers):
        speaker_colors[speaker] = colors[i % len(colors)]
    
    return speaker_colors