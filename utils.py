import os
import re
import unicodedata
import math
import glob


#Convirte segundos a formato de timecode SRT
def seconds_to_timecode(sec):
    total_ms = int(math.floor(sec*1000))
    hh = total_ms // 3600000
    mm = (total_ms % 3600000)//60000
    ss = ((total_ms %60000)//1000)
    ms = (total_ms % 1000)
    return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"


#Convirte string de tempo srt a segundos
def time_str_to_sec(time_str: str) -> float:

    # time_str en formato "hh:mm:ss,ms"
    parts = time_str.split(":")
    hh = int(parts[0])
    mm = int(parts[1])
    ss, ms = parts[2].split(",")
    total = hh*3600 + mm*60 + int(ss) + int(ms)/1000
    return total


#Esto convirte o nombre do archivo a un formato seguro para o proxecto, elimina caracteres complicados para evitar errores
def sanitize_filename(filename: str) -> str:

    filename = unicodedata.normalize('NFD', filename)
    filename = ''.join(c for c in filename if unicodedata.category(c) != 'Mn')
    filename = filename.replace(' ', '_')
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    filename = re.sub(r'_+', '_', filename)
    filename = filename.strip('_')
    
    return filename


def remove_previous_srt():
    """Elimina archivos SRT anteriores de /data para evitar conflictos, agora non deberia haber problema pero manteñoa"""

    srt_files = glob.glob("/data/*")
    if srt_files:
        print(f" Borrando SRT anteriores => {srt_files}")
        for path in srt_files:
            try:
                os.remove(path)
            except Exception as e:
                print(f"   error ao eliminar {path}: {e}")
    else:
        print("non habia srts anteriores en /data.")


#Esta funcion esta feita para correxir o erro de que a última frase que se cantou se quede en pantalla cando empeza un solo de instrumental. #HAI QUE REVISAR OUTRA SOLUCION!!!
def clean_abnormal_segments(word_segments, max_word_duration=3.0):

    if not word_segments:
        return word_segments
    
    cleaned_segments = []
    
    for i, segment in enumerate(word_segments):
        duration = segment["end"] - segment["start"]
        
        if duration > max_word_duration:
            #print(f"segmento largo detectado '{segment['word']}' dura {duration:.1f}s")
            
            corrected_segment = segment.copy()
            corrected_segment["end"] = segment["start"] + max_word_duration
            
            #print(f"corrixir a duracion a: {max_word_duration}s")
            cleaned_segments.append(corrected_segment)
        else:
            cleaned_segments.append(segment)
    
    return cleaned_segments
