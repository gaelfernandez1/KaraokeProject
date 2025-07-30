import os
import time
import traceback
from moviepy.editor import AudioFileClip, VideoFileClip, CompositeAudioClip, CompositeVideoClip

from config import VOLUME_VOCAL, ALTO_VIDEO, MARXE_INFERIOR_SUBTITULO
from audio_processing import video_to_mp3, separate_stems_cli, call_whisperx_endpoint, call_whisperx_endpoint_manual
from video_processing import normalize_video
from srt_processing import parse_word_srt, group_word_segments
from text_processing import normalize_manual_lyrics
from karaoke_rendering import create_karaoke_text_clip
from utils import remove_previous_srt, clean_abnormal_segments, sanitize_filename



#Este é o create para a version automática. WhisperX transcribe él mismo, despois parsease o SRT en tokens
#agrupanse en frases cada N palabras e despois renderizase o karaoke

def create(video_path: str, enable_diarization: bool = False, hf_token: str = None):

    remove_previous_srt()     ##Borro os srts anteriores por si acaso me daban conflicto ao ir probando a misma cancion repetidas veces
 
    # Normalizo o video. Por que? Porque añadin a parte de poder meter un MP4 para poder recortar videos e facer que
    # ocupen menos, para facer ensayo e error mais rapidamente. Entonces necesito que o formato do video do link de YT
    # e o formato do Mp4 sean o mesmo, porque si os subtitulos non son iguais non me sirve de nada practicar cos mp4s.
    try:
        video_path = normalize_video(video_path)
    except Exception as erro_normalizacion:      
        print(f" Error na normalización: {erro_normalizacion}, continuando co video original")
    
    ruta_audio = video_to_mp3(video_path)
    if not ruta_audio:
        return ""
    
    
    ruta_voz, ruta_musica = separate_stems_cli(ruta_audio)
    
    
    if not ruta_voz or not ruta_musica:
        return ""    
    
    whisper_response = call_whisperx_endpoint(ruta_voz, enable_diarization, hf_token)
    archivoSRT = ruta_voz.replace(".wav", "_whisperx.srt")
    
    # Esperamos un pouco para que whisperx genere o archivo 
    tempo_maximo = 30  
    tempo_esperado = 0
    while not os.path.exists(archivoSRT) and tempo_esperado < tempo_maximo:
        time.sleep(1)
        tempo_esperado += 1
    
    if not os.path.exists(archivoSRT):          #se non encontra o srt despois do tempo ese, return ""
        return ""
    
    if os.path.getsize(archivoSRT) == 0:        #Esto é para asegurar que o srt non esta vacio
        return ""
    
    # Parsear o srt en segmentos de palabra
    segmentos_palabras = parse_word_srt(archivoSRT)
    if not segmentos_palabras:
        print("Non hai segmentos de palabra")
        return ""
    
    #Esto é para que desapareza a ultima frase cando empeza un sólo de instrumental. Pode ser contraproducente.
    segmentos_palabras = clean_abnormal_segments(segmentos_palabras)    
    palabras_por_frase = 10                          #Van aparecer 10 palabras por frase
    grupos_texto = []
    for i in range(0, len(segmentos_palabras), palabras_por_frase):
        segmentos_actuais = segmentos_palabras[i:i+palabras_por_frase]

        # constrúo a linea unindo as palabras destos segmentos
        texto_linha = " ".join([w["word"] for w in segmentos_actuais])
        grupos_texto.append({
            "line_text": texto_linha,
            "start": segmentos_actuais[0]["start"],
            "end":   segmentos_actuais[-1]["end"],
            "words": segmentos_actuais
        })
    
    try:
        audio_musica  = AudioFileClip(ruta_musica).set_fps(44100)
        audio_voz = AudioFileClip(ruta_voz).volumex(VOLUME_VOCAL).set_fps(44100)
        audio_combinado = CompositeAudioClip([audio_musica, audio_voz])
        print(f" Audio combinado OK, dura: {audio_combinado.duration}s")
    except Exception as erro_audio:
        print(f" Error cargando audio: {erro_audio}")
        return ""
    
    try:
        video_fondo = VideoFileClip(video_path).set_duration(audio_combinado.duration).set_fps(30)
        print(f" Video cargado OK, dura: {video_fondo.duration}s, e ocupa: {video_fondo.size}")
    except Exception as erro_video:
        return ""
    
    video_escurecido = video_fondo.fl_image(lambda img: (img*0.3).astype("uint8"))
    
    #Crear e posicionar os clips de karaoke
    clips_karaoke = []
    for indice, grupo in enumerate(grupos_texto):

        # Aseguro a misma ventana de teempo e posicion para cada subtitulo
        inicio_tempo    = max(grupo["start"] - 0.5, 0)        # aparece 0.5 segundos antes
        duracion_total = grupo["end"] - grupo["start"] + 1.0  #1 segundo despois
        
        #Para obter a linea siguiente (se hai)
        proxima_linha = grupos_texto[indice + 1] if indice + 1 < len(grupos_texto) else None
        
        # Creo o clip co mismo avance e padding para todos
        clip_texto = create_karaoke_text_clip(grupo, next_line_info=proxima_linha, advance=0.5, duration_padding=0.5)
        clip_texto = clip_texto.set_start(inicio_tempo).set_duration(duracion_total)
        
        #POSICIONS FIJAS, importante, porque daba muitos problemas
        posicion_inferior = ALTO_VIDEO - MARXE_INFERIOR_SUBTITULO
        clip_texto = clip_texto.set_position(('center', posicion_inferior))
        clips_karaoke.append(clip_texto)    
        video_final = CompositeVideoClip([video_escurecido] + clips_karaoke).set_audio(audio_combinado)
    
    nome_video_base = os.path.basename(video_path).replace("_normalized", "")
    nome_video_seguro = sanitize_filename(nome_video_base)
    nome_saida = f"karaoke_{nome_video_seguro}"

    
    if not os.path.exists("./output"):
        os.makedirs("./output")
    ruta_saida = os.path.join("./output", nome_saida)
    try:

        video_final.write_videofile(ruta_saida, fps=30, threads=4)
        
        if os.path.exists(ruta_saida) and os.path.getsize(ruta_saida) > 0:
            print(f" Video generado correctamente: {ruta_saida}")
        else:
            print("O archivo non se creou ben")
            return ""
            
    except Exception as errorEscritura:
        #logs para verificar errores. Moitos problemas aqui. MOSTRAR TRACEBACK enteiro 
        print(f" error de escritura de video => {errorEscritura}")
        print(f" Traceback completo: {traceback.format_exc()}")
        return ""
    print(f" Terminado => {nome_saida}")
    return nome_saida




# A outra variante, uso de FORCED ALIGNMENT
def create_with_manual_lyrics(video_path: str, manual_lyrics: str, language=None, enable_diarization: bool = False, hf_token: str = None) -> str:

    remove_previous_srt()
    letras_normalizadas = normalize_manual_lyrics(manual_lyrics)
    
    #Forzar normalizado porque se non os subtitulos poden salir diferentes en algunhas ocasions
    ruta_video_orixinal = video_path
    try:
        ruta_normalizada = normalize_video(video_path)
        if ruta_normalizada != video_path:
            video_path = ruta_normalizada
        else:
            print("")
    except Exception as erro_norm:
        print(f"error na normalización: {erro_norm}, continuando co video orixinal")
    
    ruta_audio = video_to_mp3(video_path)
    if not ruta_audio:
        return ""
    
    ruta_voz, ruta_musica = separate_stems_cli(ruta_audio)
    if not ruta_voz or not ruta_musica:
        print(" Falta ou vocals ou music")
        return ""    
    
    # Endpoint pero da letra manual con parámetros de diarization
    whisper_response = call_whisperx_endpoint_manual(ruta_voz, letras_normalizadas, language, enable_diarization, hf_token)
    archivoSRT = ruta_voz.replace(".wav","_whisperx.srt")
    
    
    tempo_limite = 30  
    tempo_transcorrido = 0
    while not os.path.exists(archivoSRT) and tempo_transcorrido < tempo_limite:
        time.sleep(1)    
        tempo_transcorrido += 1
    
    if not os.path.exists(archivoSRT):
        print(f"non se encontrou o srt {tempo_limite}s ")
        return ""
    
    if os.path.getsize(archivoSRT) == 0:
        return ""
    
    # DIFERENTE: agrupanse as palabras segun a letra manual
    segmento_palabras = parse_word_srt(archivoSRT)
    grupos_manuais = group_word_segments(letras_normalizadas, segmento_palabras)
    if not grupos_manuais:
        print("error na agrupacion")
        return ""
    
    #Compoñer con moviepy
    try:
        audio_musica = AudioFileClip(ruta_musica).set_fps(44100)
        audio_voces = AudioFileClip(ruta_voz).volumex(VOLUME_VOCAL).set_fps(44100)
        audio_mesturado = CompositeAudioClip([audio_musica, audio_voces])
        #print(f"audio combinado OK, dura: {audio_mesturado.duration}s")
    except Exception as erro_audio:
        print(f"error cargando audio {erro_audio}")
        return ""
    
    try:
        video_fondo = VideoFileClip(video_path).set_duration(audio_mesturado.duration).set_fps(30)
        #print(f" Video OK, dura: {video_fondo.duration}s, e ocupa: {video_fondo.size}")
    except Exception as erro_video:

        # Intentase co video original se onormalizado falla
        if video_path != ruta_video_orixinal:
            try:
                video_fondo = VideoFileClip(ruta_video_orixinal).set_duration(audio_mesturado.duration).set_fps(30)
            except Exception as erro_video2:
                print(f"fallo tamen co video orixinal {erro_video2}")
                return ""
        else:
            return ""
    
    video_escurecido = video_fondo.fl_image(lambda img: (img*0.3).astype("uint8"))
    


    clips_karaoke = []
    for indice, grupo in enumerate(grupos_manuais):
        #mostrase medio segundo antes por comodidad
        inicio_compensado = max(grupo["start"] - 0.5, 0)
        duracion_extendida = grupo["end"] - grupo["start"] + 1.0  
        
        # arreglo por frases largas. MIRAR CAL SERIA O LIMITE!!!!
        linha_seguinte = grupos_manuais[indice + 1] if indice + 1 < len(grupos_manuais) else None
        clip_texto = create_karaoke_text_clip(grupo, next_line_info=linha_seguinte, advance=0.5, duration_padding=0.5)
        

        posicion_baixo = ALTO_VIDEO - MARXE_INFERIOR_SUBTITULO
        
        clip_texto = clip_texto.set_start(inicio_compensado).set_duration(duracion_extendida)
        clip_texto = clip_texto.set_position(('center', posicion_baixo))
        
        clips_karaoke.append(clip_texto) 

    # Faise o video final superpoñendo os clips de karaoke sobre o fondo
    video_final = CompositeVideoClip([video_escurecido] + clips_karaoke).set_audio(audio_mesturado)
    

    nome_video_base = os.path.basename(video_path)
    nome_video_seguro = sanitize_filename(nome_video_base)
    nombreArchivo = f"karaoke_manual_{nome_video_seguro}"


    if not os.path.exists("./output"):
        os.makedirs("./output")
    ruta_saida = os.path.join("./output", nombreArchivo)
    
    try:
        video_final.write_videofile(ruta_saida, fps=30, threads=4)
        
        if os.path.exists(ruta_saida) and os.path.getsize(ruta_saida) > 0:
            print(f" Video generado correctamente: {ruta_saida}")
        else:
            print("non se creou o archivo de salida")
            return ""
            
    except Exception as errorEscritura:
        print(f"error de escritura => {errorEscritura}")
        # O mismo que no automatico, mostramos mais info do error debido a varios problemas
        print(f"Traceback completo: {traceback.format_exc()}")
        return ""
    print(f"Final => {nombreArchivo}")
    return nombreArchivo


def generate_instrumental(video_path: str) -> str:

    
    try:
        video_path = normalize_video(video_path)
    except Exception as erro_normalizacion:      
        print(f"Error na normalización: {erro_normalizacion}, continuando co video orixinal")
    
    ruta_audio = video_to_mp3(video_path)
    if not ruta_audio:
        return ""
    
    ruta_voz, ruta_musica = separate_stems_cli(ruta_audio)
    if not ruta_musica:
        print("Error separando a instrumental ")
        return ""
    
    nome_video_base = os.path.basename(video_path).replace("_normalized", "")
    nome_video_seguro = sanitize_filename(nome_video_base)
    nome_saida = f"instrumental_{nome_video_seguro.replace('.mp4', '.wav')}"
    
    if not os.path.exists("./output"):
        os.makedirs("./output")
    
    ruta_saida = os.path.join("./output", nome_saida)
    
    try:
        import shutil
        shutil.copy2(ruta_musica, ruta_saida)
        
        if os.path.exists(ruta_saida) and os.path.getsize(ruta_saida) > 0:
            print(f"Instrumental xerada. {ruta_saida}")
        else:
            return ""
            
    except Exception as error_copia:
        return ""
    
    print(f"Feito! {nome_saida}")
    return nome_saida
