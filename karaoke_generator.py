import os
import time
import traceback
from moviepy.editor import AudioFileClip, VideoFileClip, CompositeAudioClip, CompositeVideoClip

from config import VOLUME_VOCAL, ALTO_VIDEO, MARXE_INFERIOR_SUBTITULO
from audio_processing import video_to_mp3, separate_stems_cli, call_whisperx_endpoint, call_whisperx_endpoint_manual, transcribe_with_faster_whisper
from video_processing import normalize_video
from srt_processing import parse_word_srt, group_word_segments, group_word_segments_automatic
from text_processing import normalize_manual_lyrics
from karaoke_rendering import create_karaoke_text_clip
from utils import remove_previous_srt, clean_abnormal_segments, sanitize_filename
from database import save_song_to_database
from metadata_utils import generate_song_metadata



#Este é o create para a version automática. WhisperX transcribe él mismo, despois parsease o SRT en tokens
#agrupanse en frases cada N palabras e despois renderizase o karaoke

def create(video_path: str, enable_diarization: bool = False, hf_token: str = None, whisper_model: str = "small",
           source_type: str = "upload", source_url: str = None, save_to_db: bool = True):
    
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
    
    #cambio a faster whisper para o automatico por culpa do VAD de whisperx.
    transcribed_lyrics = transcribe_with_faster_whisper(ruta_voz, whisper_model)
    if not transcribed_lyrics:
        return ""
    
    
    #solucion medio casera, normalizo as letras como se foran manuales. mais ou menos fago todo o posible como se fora manual menos a trancricion
    letras_normalizadas = normalize_manual_lyrics(transcribed_lyrics)
    
    whisper_response = call_whisperx_endpoint_manual(ruta_voz, letras_normalizadas, None, enable_diarization, hf_token, whisper_model)
    archivoSRT = ruta_voz.replace(".wav", "_whisperx.srt")
    
    tempo_maximo = 30  
    tempo_esperado = 0
    while not os.path.exists(archivoSRT) and tempo_esperado < tempo_maximo:
        time.sleep(1)
        tempo_esperado += 1
    
    if not os.path.exists(archivoSRT):
        print(f"Error: Nnn se xerou o arquivo SRT despois d {tempo_maximo}s")    #se non encontra o srt despois do tempo ese, return ""
        return ""
    
    if os.path.getsize(archivoSRT) == 0:  #Esto é para asegurar que o srt non esta vacio
        print("error: O arquivo SRT está vacio")
        return ""
    
    #fixen unha funcion para agrupar frases no modo automatico, porque non pode ser con saltos de linea
    segmento_palabras = parse_word_srt(archivoSRT)
    grupos_texto = group_word_segments_automatic(segmento_palabras, max_words_per_phrase=6, max_duration=3.5)
    if not grupos_texto:
        return ""
    
    print(f"Creados {len(grupos_texto)} grupos de frases (debug) ")
    
    # Composición con moviepy (igual q en modo manual)
    try:
        audio_musica = AudioFileClip(ruta_musica).set_fps(44100)
        audio_voces = AudioFileClip(ruta_voz).volumex(VOLUME_VOCAL).set_fps(44100)
        audio_mesturado = CompositeAudioClip([audio_musica, audio_voces])
    except Exception as erro_audio:
        print(f"Error cargando audio {erro_audio}")
        return ""
    
    try:
        video_fondo = VideoFileClip(video_path).set_duration(audio_mesturado.duration).set_fps(30)
    except Exception as erro_video:
        print(f"Error cargando video {erro_video}")
        return ""
    
    video_escurecido = video_fondo.fl_image(lambda img: (img*0.3).astype("uint8"))
    
   
    clips_karaoke = []
    for indice, grupo in enumerate(grupos_texto):
        #mostrar medio segundo antes por comodidad
        inicio_compensado = max(grupo["start"] - 0.5, 0)
        duracion_extendida = grupo["end"] - grupo["start"] + 1.0  
        
        linha_seguinte = grupos_texto[indice + 1] if indice + 1 < len(grupos_texto) else None
        clip_texto = create_karaoke_text_clip(grupo, next_line_info=linha_seguinte, advance=0.5, duration_padding=0.5)
        
        posicion_baixo = ALTO_VIDEO - MARXE_INFERIOR_SUBTITULO
        
        clip_texto = clip_texto.set_start(inicio_compensado).set_duration(duracion_extendida)
        clip_texto = clip_texto.set_position(('center', posicion_baixo))
        
        clips_karaoke.append(clip_texto) 

    video_final = CompositeVideoClip([video_escurecido] + clips_karaoke).set_audio(audio_mesturado)
    
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
    
    #Aqui gardo os archivos separados para o tema do reprodutor web
    try:
        video_sin_audio = video_escurecido
        ruta_video_silencioso = ruta_saida.replace(".mp4", "_video_only.mp4")
        video_sin_audio.write_videofile(ruta_video_silencioso, fps=30, threads=4, audio=False)
        
        nome_sin_extension = nome_video_seguro.replace('.mp4', '')
        ruta_vocal_output = os.path.join("./output", f"vocal_{nome_sin_extension}.wav")
        ruta_instrumental_output = os.path.join("./output", f"instrumental_{nome_sin_extension}.wav")
        
        import shutil
        shutil.copy2(ruta_voz, ruta_vocal_output)
        shutil.copy2(ruta_musica, ruta_instrumental_output)
        
    except Exception as e:
        print(f"Erro cos archivos separados: {e}")
    
    #gardar na base de datos se está habilitado
    if save_to_db:
        try:
            original_filename = os.path.basename(video_path)
            metadata = generate_song_metadata(
                original_filename=original_filename,
                karaoke_filename=nome_saida,
                source_type=source_type,
                source_url=source_url,
                processing_type="automatic",
                enable_diarization=enable_diarization,
                whisper_model=whisper_model,
                output_dir="./output"
            )
            song_id = save_song_to_database(metadata)
            print(f"Canción gardada na base de datos con ID: {song_id}")
        except Exception as e:
            print(f"Erro gardando na base de datos: {e}")
    
    return nome_saida




# A outra variante, uso de FORCED ALIGNMENT
def create_with_manual_lyrics(video_path: str, manual_lyrics: str, language=None, enable_diarization: bool = False, hf_token: str = None, whisper_model: str = "small",
                             source_type: str = "upload", source_url: str = None, save_to_db: bool = True) -> str:

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
    whisper_response = call_whisperx_endpoint_manual(ruta_voz, letras_normalizadas, language, enable_diarization, hf_token, whisper_model)
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
    
    #Aqui gardo os archivos separados para o tema do reprodutor web
    try:
        video_sin_audio = video_escurecido
        ruta_video_silencioso = ruta_saida.replace(".mp4", "_video_only.mp4")
        video_sin_audio.write_videofile(ruta_video_silencioso, fps=30, threads=4, audio=False)
        
        nome_sin_extension = nome_video_seguro.replace('.mp4', '')
        ruta_vocal_output = os.path.join("./output", f"vocal_{nome_sin_extension}.wav")
        ruta_instrumental_output = os.path.join("./output", f"instrumental_{nome_sin_extension}.wav")
        
        import shutil
        shutil.copy2(ruta_voz, ruta_vocal_output)
        shutil.copy2(ruta_musica, ruta_instrumental_output)
        
    except Exception as e:
        print(f"Error cos arquivos separados: {e}")
    
    #Gardar na base de datos 
    if save_to_db:
        try:
            original_filename = os.path.basename(video_path)
            metadata = generate_song_metadata(
                original_filename=original_filename,
                karaoke_filename=nombreArchivo,
                source_type=source_type,
                source_url=source_url,
                processing_type="manual_lyrics",
                manual_lyrics=manual_lyrics,
                language=language,
                enable_diarization=enable_diarization,
                whisper_model=whisper_model,
                output_dir="./output"
            )
            song_id = save_song_to_database(metadata)
            print(f"canción con letras manuais gardada na base de datos con ID: {song_id}")
        except Exception as e:
            print(f"Erro gardando na base de datos: {e}")
    
    return nombreArchivo


def generate_instrumental(video_path: str, source_type: str = "upload", source_url: str = None, save_to_db: bool = True) -> str:

    
    #solo normalizar se é un video mp4, non se é mp3
    if not video_path.lower().endswith('.mp3'):
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
    
    if nome_video_seguro.lower().endswith('.mp4'):
        nome_saida = f"instrumental_{nome_video_seguro.replace('.mp4', '.wav')}"
    elif nome_video_seguro.lower().endswith('.mp3'):
        nome_saida = f"instrumental_{nome_video_seguro.replace('.mp3', '.wav')}"
    else:
        #fallback: añadir extension .wav
        nome_saida = f"instrumental_{nome_video_seguro}.wav"
    
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
    
    #gardar instrumental na base de datos se está activado
    if save_to_db:
        try:
            from moviepy.editor import AudioFileClip
            
            nome_original = os.path.basename(video_path)
            title = nome_original.replace('_normalized', '')
            if title.lower().endswith('.mp4'):
                title = title[:-4]   # eliminar .mp4
            elif title.lower().endswith('.mp3'):
                title = title[:-4]    # eliminar .mp3
            title = f"[Instrumental] {title}"
            
            file_size = os.path.getsize(ruta_saida)
            
            try:
                audio_clip = AudioFileClip(ruta_saida)
                duration = audio_clip.duration
                audio_clip.close()
            except:
                duration = None
            
            song_data = {
                'title': title,
                'original_filename': nome_original,
                'karaoke_filename': nome_saida,  #este e o principal archivo para instrumentales
                'video_only_filename': None,
                'vocal_filename': None,
                'instrumental_filename': nome_saida,
                'source_type': source_type,
                'source_url': source_url,
                'processing_type': 'instrumental',
                'manual_lyrics': None,
                'language': None,
                'enable_diarization': False,
                'file_size': file_size,
                'duration': duration
            }
            
            song_id = save_song_to_database(song_data)
            
        except Exception as e:
            print(f"Erro gardando instrumental na bd: {e}")
    
    return nome_saida
