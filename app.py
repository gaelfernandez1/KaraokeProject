import os
import yt_dlp
import json
from flask import Flask, request, send_file, render_template, redirect, url_for, jsonify, session
from werkzeug.utils import secure_filename

from karaoke_generator import create, create_with_manual_lyrics, generate_instrumental
from gpu_utils import print_system_summary
from database import init_database
from security_config import setup_security, validate_file_size, sanitize_filename

#meter celery no proyecto
from celery_app import celery
from celery_tasks import process_automatic_karaoke, process_manual_lyrics_karaoke, process_instrumental_only

app = Flask(__name__)

print_system_summary()
init_database()

DIRECTORIO_ENTRADA = "input"
DIRECTORIO_SAIDA = "output"
os.makedirs(DIRECTORIO_ENTRADA, exist_ok=True)
os.makedirs(DIRECTORIO_SAIDA, exist_ok=True)

EXTENSIONES_PERMITIDAS = {"mp4"}
EXTENSIONES_AUDIO_PERMITIDAS = {"wav", "mp3"}
EXTENSIONES_INSTRUMENTAL_PERMITIDAS = {"mp4", "mp3"}


# PAra comprobar si o archivo ten unha extension permitida
def archivo_permitido(nome_arquivo: str) -> bool:
    return "." in nome_arquivo and nome_arquivo.rsplit(".", 1)[1].lower() in EXTENSIONES_PERMITIDAS



def archivo_instrumental_permitido(nome_arquivo: str) -> bool:
    return "." in nome_arquivo and nome_arquivo.rsplit(".", 1)[1].lower() in EXTENSIONES_INSTRUMENTAL_PERMITIDAS


def descargar_video_youtube(url: str, directorio_saida: str = DIRECTORIO_ENTRADA) -> str:
    """ Funcion para descargar un video de YT e devolve a ruta do mp4 descargado """

    opcions_ydl = {
        'outtmpl': os.path.join(directorio_saida, '%(title)s.%(ext)s'),
        'format': 'bestvideo[height>=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',   # Esta combinacion funciona, varias que probei antes daban diversos errores
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(opcions_ydl) as ydl:
        info = ydl.extract_info(url, download=True)
        nome_ficheiro = ydl.prepare_filename(info)
        return nome_ficheiro



@app.route("/", methods=["GET"])
def inicio():
    return render_template("index.html")

#asincronia
@app.route("/generate", methods=["POST"])
def xerar_karaoke():
    ruta_video = None
    arquivo_subido = request.files.get("video_file")
    if arquivo_subido and arquivo_subido.filename and archivo_permitido(arquivo_subido.filename):
        nome_ficheiro = secure_filename(arquivo_subido.filename)
        ruta_video = os.path.join(DIRECTORIO_ENTRADA, nome_ficheiro)
        arquivo_subido.save(ruta_video)
    else:
        url_youtube = request.form.get("youtube_url", "").strip()
        if not url_youtube:
            return "Debes mandar ou un mp4 ou un link de Youtube", 400
        try:
            ruta_video = descargar_video_youtube(url_youtube)
        except Exception as e:
            return f"Error descargando vídeo: {e}", 500
    
    enable_diarization = request.form.get("enable_diarization") == "true"
    hf_token = request.form.get("hf_token", "").strip() if enable_diarization else None
    
    source_type = "upload" if arquivo_subido else "youtube"
    source_url = url_youtube if not arquivo_subido else None
    
    task = process_automatic_karaoke.delay(
        ruta_video, enable_diarization, hf_token, source_type, source_url, True
    )
    
    session['current_task_id'] = task.id
    session['task_type'] = 'automatic'
    
    return redirect(url_for('mostrar_progreso', task_id=task.id))


@app.route("/manual_lyrics_form", methods=["GET"])
def formulario_letras_manuales():
    return render_template("manual_lyrics_form.html")


@app.route("/process_manual_lyrics", methods=["POST"])
def procesar_letras_manuales():
    ruta_video = None
    arquivo_subido = request.files.get("video_file")
    if arquivo_subido and arquivo_subido.filename and archivo_permitido(arquivo_subido.filename):
        nome_ficheiro = secure_filename(arquivo_subido.filename)
        ruta_video = os.path.join(DIRECTORIO_ENTRADA, nome_ficheiro)
        arquivo_subido.save(ruta_video)
    else:
        url_youtube = request.form.get("youtube_url", "").strip()
        if not url_youtube:
            return "Tes que subir un mp4 ou un link de Youtube", 400
        try:
            ruta_video = descargar_video_youtube(url_youtube)
        except Exception as e:
            return f"Erro descargando vídeo: {e}", 500

    letra_manual = request.form.get("manual_lyrics", "").strip()
    if not letra_manual:
        return "Falta o texto da letra.", 400
    
    enable_diarization = request.form.get("enable_diarization") == "true"
    hf_token = request.form.get("hf_token", "").strip() if enable_diarization else None
    
    source_type = "upload" if arquivo_subido else "youtube"
    source_url = url_youtube if not arquivo_subido else None
    
    task = process_manual_lyrics_karaoke.delay(
        ruta_video, letra_manual, None, enable_diarization, hf_token, 
        source_type, source_url, True
    )
    
    session['current_task_id'] = task.id
    session['task_type'] = 'manual_lyrics'
    
    return redirect(url_for('mostrar_progreso', task_id=task.id))


@app.route("/generate_instrumental", methods=["POST"])
def xerar_instrumental():
    ruta_video = None
    arquivo_subido = request.files.get("video_file")
    if arquivo_subido and arquivo_subido.filename and archivo_instrumental_permitido(arquivo_subido.filename):
        nome_ficheiro = secure_filename(arquivo_subido.filename)
        ruta_video = os.path.join(DIRECTORIO_ENTRADA, nome_ficheiro)
        arquivo_subido.save(ruta_video)
    else:
        url_youtube = request.form.get("youtube_url", "").strip()
        if not url_youtube:
            return "Tes que mandar un mp4/mp3 ou un link de YouTube", 400
        try:
            ruta_video = descargar_video_youtube(url_youtube)
        except Exception as e:
            return f"Erro descargando vídeo: {e}", 500
    
    source_type = "upload" if arquivo_subido else "youtube"
    source_url = url_youtube if not arquivo_subido else None
    
    task = process_instrumental_only.delay(ruta_video, source_type, source_url, True)
    
    session['current_task_id'] = task.id
    session['task_type'] = 'instrumental'
    
    return redirect(url_for('mostrar_progreso', task_id=task.id))


#hai q meter novos endpoints para as tareas asincronas

@app.route("/progress/<task_id>")
def mostrar_progreso(task_id):
    return render_template("progress.html", task_id=task_id)

@app.route("/api/task_status/<task_id>")
def estado_tarea(task_id):
    try:
        task_result = celery.AsyncResult(task_id)
        
        if task_result.state == 'PENDING':
            response = {
                'state': task_result.state,
                'status': 'Tarea en cola...'
            }
        elif task_result.state == 'PROGRESS':
            response = {
                'state': task_result.state,
                'status': task_result.info.get('status', 'Procesando...'),
                'current': task_result.info.get('current', 0),
                'total': task_result.info.get('total', 100)
            }
        elif task_result.state == 'SUCCESS':
            response = {
                'state': task_result.state,
                'status': 'Completado!',
                'result': task_result.info.get('result'),
                'message': task_result.info.get('message', 'Procesamento completado')
            }
        elif task_result.state == 'FAILURE':
            response = {
                'state': task_result.state,
                'status': task_result.info.get('status', 'Erro en procesameento'),
                'error': str(task_result.info.get('error', 'Erro descoñecido'))
            }
        elif task_result.state == 'REVOKED':
            response = {
                'state': task_result.state,
                'status': 'Tarefa cancelada',
                'message': 'o procesamiento foi cancelado'
            }
        else:
            response = {
                'state': task_result.state,
                'status': f'Estado: {task_result.state}'
            }
            
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'state': 'ERROR',
            'status': f'Error obtendo estado: {str(e)}'
        }), 500

@app.route("/api/cancel_task/<task_id>", methods=["POST"])
def cancelar_tarea(task_id):
    try:
        #revocar a tarea en celery
        celery.control.revoke(task_id, terminate=True, signal='SIGKILL')
        
        if session.get('current_task_id') == task_id:
            session.pop('current_task_id', None)
            session.pop('task_type', None)
        
        return jsonify({
            'status': 'success',
            'message': 'Tarefa cancelada'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error cancelando: {str(e)}'
        }), 500

@app.route("/api/download_result/<task_id>")
def descargar_resultado_tarea(task_id):
    try:
        task_result = celery.AsyncResult(task_id)
        
        if task_result.state != 'SUCCESS':
            return jsonify({'error': 'A tarefa non se completou exitosamente'}), 400

        resultado = task_result.info.get('result')
        if not resultado:
            return jsonify({'error': 'Non hai resultado'}), 404
            
        #redirigir ao reproductor
        task_type = session.get('task_type', 'unknown')
        if task_type in ['automatic', 'manual_lyrics']:
            return redirect(url_for('reproductor_karaoke', filename=resultado))
        elif task_type == 'instrumental':
            ruta_saida = os.path.join(DIRECTORIO_SAIDA, resultado)
            if os.path.exists(ruta_saida):
                return send_file(ruta_saida, as_attachment=True, download_name=resultado)
            else:
                return jsonify({'error': 'Arquivo non encontrado'}), 404
        else:
            return jsonify({'error': 'Tipo de tarefa descoñecido'}), 400

    except Exception as e:
        return jsonify({'error': f'Erro descargando resultado: {str(e)}'}), 500

















@app.route("/player/<filename>")
def reproductor_karaoke(filename):

    ruta_video = os.path.join(DIRECTORIO_SAIDA, filename)
    if not os.path.exists(ruta_video):
        return "Arquivo non encontrado", 404
    
    if filename.startswith("karaoke_manual_"):
        nome_base = filename.replace("karaoke_manual_", "").replace(".mp4", "")
    elif filename.startswith("karaoke_"):
        nome_base = filename.replace("karaoke_", "").replace(".mp4", "")
    else:
        nome_base = filename.replace(".mp4", "")
    
    return render_template("player.html", 
                         video_filename=filename,
                         base_name=nome_base)


@app.route("/serve_video/<filename>")
def servir_video(filename):

    ruta_archivo = os.path.join(DIRECTORIO_SAIDA, filename)
    if not os.path.exists(ruta_archivo):
        return "Archivo non encontrado", 404
    
    return send_file(ruta_archivo, mimetype='video/mp4')


@app.route("/serve_audio/<filename>")
def servir_audio(filename):

    ruta_archivo = os.path.join(DIRECTORIO_SAIDA, filename)
    if not os.path.exists(ruta_archivo):
        return "Arquivo non encontrado", 404
    
    return send_file(ruta_archivo, mimetype='audio/wav')


@app.route("/download/<filename>")
def descargar_archivo(filename):

    ruta_arquivo = os.path.join(DIRECTORIO_SAIDA, filename)
    if not os.path.exists(ruta_arquivo):
        return "Arquivo non encontrado", 404
    
    tamano_ficheiro = os.path.getsize(ruta_arquivo)
    nome_descarga_seguro = secure_filename(filename)
    
    try:
        response = send_file(ruta_arquivo, as_attachment=True, download_name=nome_descarga_seguro)
        
        if filename.endswith('.mp4'):
            response.headers["Content-Type"] = "video/mp4"
        elif filename.endswith('.wav'):
            response.headers["Content-Type"] = "audio/wav"
        
        response.headers["Content-Length"] = str(tamano_ficheiro)
        return response
    except Exception as e:
        return f"Errro enviando archivo: {e}", 500


@app.route("/library")
def biblioteca_cancions():
    """Páxina da biblioteca de cancións gardadas"""
    from database import get_all_songs, get_database_stats
    from metadata_utils import format_file_size, format_duration
    
    try:
        songs = get_all_songs()
        stats = get_database_stats()
        
        # Formatear tamaños e duracións para mostrar
        for song in songs:
            song['formatted_file_size'] = format_file_size(song['file_size'] or 0)
            song['formatted_duration'] = format_duration(song['duration'])
        
        return render_template("library.html", songs=songs, stats=stats)
    except Exception as e:
        return f"Erro cargando biblioteca: {e}", 500


@app.route("/library/search")
def buscar_cancions():
    """Endpoint para buscar cancións na biblioteca"""
    from database import get_songs_by_search
    from metadata_utils import format_file_size, format_duration
    
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('biblioteca_cancions'))
    
    try:
        songs = get_songs_by_search(query)
        
        # Formatear tamaños e duracións
        for song in songs:
            song['formatted_file_size'] = format_file_size(song['file_size'] or 0)
            song['formatted_duration'] = format_duration(song['duration'])
        
        return render_template("library.html", songs=songs, search_query=query)
    except Exception as e:
        return f"Erro buscando cancións: {e}", 500


@app.route("/library/play/<int:song_id>")
def reproducir_dende_biblioteca(song_id):
    """Reproduce unha canción dende a biblioteca usando o seu ID"""
    from database import get_song_by_id, update_last_played
    
    try:
        song = get_song_by_id(song_id)
        if not song:
            return "Canción non encontrada na biblioteca", 404
        
        # Verificar que o arquivo existe
        ruta_video = os.path.join(DIRECTORIO_SAIDA, song['karaoke_filename'])
        if not os.path.exists(ruta_video):
            return "Arquivo de video non encontrado", 404
        
        # Actualizar timestamp da última reprodución
        update_last_played(song_id)
        
        # Redirigir ao reproductor
        return redirect(url_for('reproductor_karaoke', filename=song['karaoke_filename']))
        
    except Exception as e:
        return f"Erro reproducindo canción: {e}", 500


@app.route("/library/delete/<int:song_id>", methods=["POST"])
def borrar_cancion_biblioteca(song_id):
    """Borra unha canción da biblioteca e os seus arquivos"""
    from database import get_song_by_id, delete_song
    
    try:
        song = get_song_by_id(song_id)
        if not song:
            return "Canción non encontrada na biblioteca", 404
        
        # Lista de arquivos para borrar
        arquivos_para_borrar = []
        
        # Arquivo principal de karaoke
        if song['karaoke_filename']:
            arquivos_para_borrar.append(os.path.join(DIRECTORIO_SAIDA, song['karaoke_filename']))
        
        # Video sin audio
        if song['video_only_filename']:
            arquivos_para_borrar.append(os.path.join(DIRECTORIO_SAIDA, song['video_only_filename']))
        
        # Arquivos de audio
        if song['vocal_filename']:
            arquivos_para_borrar.append(os.path.join(DIRECTORIO_SAIDA, song['vocal_filename']))
        
        if song['instrumental_filename']:
            arquivos_para_borrar.append(os.path.join(DIRECTORIO_SAIDA, song['instrumental_filename']))
        
        # Borrar arquivos do disco
        arquivos_borrados = 0
        for arquivo in arquivos_para_borrar:
            try:
                if os.path.exists(arquivo):
                    os.remove(arquivo)
                    arquivos_borrados += 1
                    print(f"Arquivo borrado: {arquivo}")
            except Exception as e:
                print(f"Erro borrando arquivo {arquivo}: {e}")
        
        # Borrar da base de datos
        if delete_song(song_id):
            print(f"Canción {song['title']} borrada da biblioteca (ID: {song_id})")
            return redirect(url_for('biblioteca_cancions'))
        else:
            return "Erro borrando canción da base de datos", 500
            
    except Exception as e:
        return f"Erro borrando canción: {e}", 500




#configurar a seguridade despois de definir as rutas(ngrok)
limiter = setup_security(app)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
