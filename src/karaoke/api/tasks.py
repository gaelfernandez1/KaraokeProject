import logging
import os
from flask import Blueprint, render_template, jsonify, session, redirect, url_for, send_file, abort

from karaoke.workers.celery_app import celery

logger = logging.getLogger(__name__)

bp = Blueprint('tasks', __name__)

DIRECTORIO_SAIDA = "output"


#hai q meter novos endpoints para as tareas asincronas

@bp.route("/progress/<task_id>")
def mostrar_progreso(task_id):
    return render_template("progress.html", task_id=task_id)

@bp.route("/api/task_status/<task_id>")
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

    except Exception:
        logger.exception("Error obtendo estado da tarefa")
        abort(500)

@bp.route("/api/cancel_task/<task_id>", methods=["POST"])
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

    except Exception:
        logger.exception(f"Error cancelando tarefa {task_id}")
        abort(500)

@bp.route("/api/download_result/<task_id>")
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
            return redirect(url_for('player.reproductor_karaoke', filename=resultado))
        elif task_type == 'instrumental':
            ruta_saida = os.path.join(DIRECTORIO_SAIDA, resultado)
            if os.path.exists(ruta_saida):
                return send_file(ruta_saida, as_attachment=True, download_name=resultado)
            else:
                return jsonify({'error': 'Arquivo non encontrado'}), 404
        else:
            return jsonify({'error': 'Tipo de tarefa descoñecido'}), 400

    except Exception:
        logger.exception(f"Erro descargando resultado da tarefa {task_id}")
        abort(500)
