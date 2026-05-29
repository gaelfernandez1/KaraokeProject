import os
from flask import Blueprint, render_template, request, redirect, url_for

from karaoke.infra.database import (
    get_all_songs, get_database_stats, get_songs_by_search,
    get_song_by_id, update_last_played, delete_song
)
from karaoke.infra.metadata_utils import format_file_size, format_duration

bp = Blueprint('library', __name__)

DIRECTORIO_SAIDA = "output"


@bp.route("/library")
def biblioteca_cancions():
    try:
        songs = get_all_songs()
        stats = get_database_stats()

        for song in songs:
            song['formatted_file_size'] = format_file_size(song['file_size'] or 0)
            song['formatted_duration'] = format_duration(song['duration'])

        return render_template("library.html", songs=songs, stats=stats)
    except Exception as e:
        return f"erro cargando biblioteca: {e}", 500


@bp.route("/library/search")
def buscar_cancions():
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('library.biblioteca_cancions'))

    try:
        songs = get_songs_by_search(query)

        for song in songs:
            song['formatted_file_size'] = format_file_size(song['file_size'] or 0)
            song['formatted_duration'] = format_duration(song['duration'])

        return render_template("library.html", songs=songs, search_query=query)
    except Exception as e:
        return f"Error buscando cancións: {e}", 500


@bp.route("/library/play/<int:song_id>")
def reproducir_dende_biblioteca(song_id):
    try:
        song = get_song_by_id(song_id)
        if not song:
            return "Canción non encontrada", 404

        ruta_video = os.path.join(DIRECTORIO_SAIDA, song['karaoke_filename'])
        if not os.path.exists(ruta_video):
            return "Arquivo de video non encontrado", 404

        update_last_played(song_id)
        return redirect(url_for('player.reproductor_karaoke', filename=song['karaoke_filename']))

    except Exception as e:
        return f"Error reproducindo canción: {e}", 500


@bp.route("/library/delete/<int:song_id>", methods=["POST"])
def borrar_cancion_biblioteca(song_id):
    try:
        song = get_song_by_id(song_id)
        if not song:
            return "Canción non encontrada na bib", 404

        arquivos_para_borrar = []

        if song['karaoke_filename']:
            arquivos_para_borrar.append(os.path.join(DIRECTORIO_SAIDA, song['karaoke_filename']))
        if song['video_only_filename']:
            arquivos_para_borrar.append(os.path.join(DIRECTORIO_SAIDA, song['video_only_filename']))
        if song['vocal_filename']:
            arquivos_para_borrar.append(os.path.join(DIRECTORIO_SAIDA, song['vocal_filename']))
        if song['instrumental_filename']:
            arquivos_para_borrar.append(os.path.join(DIRECTORIO_SAIDA, song['instrumental_filename']))

        arquivos_borrados = 0
        for arquivo in arquivos_para_borrar:
            try:
                if os.path.exists(arquivo):
                    os.remove(arquivo)
                    arquivos_borrados += 1
                    print(f"Arquivo borrado: {arquivo}")
            except Exception as e:
                print(f"Erro borrando arquivo {arquivo}: {e}")

        if delete_song(song_id):
            print(f"Canción {song['title']} borrada da biblioteca (ID: {song_id})")
            return redirect(url_for('library.biblioteca_cancions'))
        else:
            return "error borrando canción", 500

    except Exception as e:
        return f"Erro borrando canción: {e}", 500
