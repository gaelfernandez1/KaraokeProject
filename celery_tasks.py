import os
import time
import traceback
from celery import current_task
from celery_app import celery, active_processes
from karaoke_generator import create, create_with_manual_lyrics, generate_instrumental
import signal


class ProcessingCancelledException(Exception):
    pass


def check_if_cancelled():
    if current_task.request.id in active_processes:
        status = active_processes[current_task.request.id].get('status')
        if status in ['REVOKED', 'CANCELLED']:
            raise ProcessingCancelledException("Tarefa cancelada")
    
    if current_task.request.called_directly is False:
        try:
            # obter o estado actual desde redis
            task_result = celery.AsyncResult(current_task.request.id)
            if task_result.state == 'REVOKED':
                raise ProcessingCancelledException("Tarefa cancelada")
        except:
            pass


@celery.task(bind=True, name='process_automatic_karaoke')
def process_automatic_karaoke(self, video_path, enable_diarization=False, hf_token=None, 
                             source_type="upload", source_url=None, save_to_db=True):
 
    task_id = self.request.id
    
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Iniciando procesamiento automático...'})
        
        check_if_cancelled()
        
        #chamar a función orixinal pero con checkeos de cancelacion
        resultado = create_with_cancellation_check(
            video_path, enable_diarization, hf_token, source_type, source_url, save_to_db
        )
        
        if not resultado:
            raise Exception("o procesamento non devolviu resultado")
            
        return {
            'status': 'completed',
            'result': resultado,
            'message': 'Karaoke automático xerado exitosamente'
        }
        
    except ProcessingCancelledException:
        cleanup_partial_files(video_path)
        self.update_state(state='REVOKED', meta={'status': 'Procesamento cancelado'})
        raise ProcessingCancelledException("Procesamento cancelado")
        
    except Exception as e:
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        print(f" Error en process_automatic_karaoke: {error_msg}")
        print(f" Traceback: {traceback_str}")
        
        self.update_state(state='FAILURE', meta={
            'status': f'Error: {error_msg}',
            'error': error_msg,
            'traceback': traceback_str
        })
        raise Exception(error_msg)


@celery.task(bind=True, name='process_manual_lyrics_karaoke')  
def process_manual_lyrics_karaoke(self, video_path, manual_lyrics, language=None, 
                                 enable_diarization=False, hf_token=None,
                                 source_type="upload", source_url=None, save_to_db=True):

    task_id = self.request.id
    
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Iniciando procesamento con letras manuales...'})
        
        check_if_cancelled()
        resultado = create_with_manual_lyrics_with_cancellation_check(
            video_path, manual_lyrics, language, enable_diarization, hf_token,
            source_type, source_url, save_to_db
        )
        
        if not resultado:
            raise Exception("o procesamento non devolviu resultado")
            
        return {
            'status': 'completed', 
            'result': resultado,
            'message': 'Karaoke cas letras manuales xerado exitosamente'
        }
        
    except ProcessingCancelledException:
        cleanup_partial_files(video_path)
        self.update_state(state='REVOKED', meta={'status': 'Procesameento cancelado'})
        raise ProcessingCancelledException("Procesamento cancelado")
        
    except Exception as e:
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        print(f"Traceback: {traceback_str}")
        
        self.update_state(state='FAILURE', meta={
            'status': f'Error: {error_msg}',
            'error': error_msg,
            'traceback': traceback_str
        })
        raise Exception(error_msg)


@celery.task(bind=True, name='process_instrumental_only')
def process_instrumental_only(self, video_path, source_type="upload", source_url=None, save_to_db=True):

    task_id = self.request.id
    
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Xerando instrumental...'})
        
        check_if_cancelled()
        
        resultado = generate_instrumental_with_cancellation_check(video_path, source_type, source_url, save_to_db)
        
        if not resultado:
            raise Exception("O procesamento non devolviu resultado")
            
        return {
            'status': 'completed',
            'result': resultado, 
            'message': 'Instrumental xerada'
        }
        
    except ProcessingCancelledException:
        cleanup_partial_files(video_path)
        self.update_state(state='REVOKED', meta={'status': 'Procesamento cancelado polo usuario'})
        raise ProcessingCancelledException("Procesamento cancelado")
        
    except Exception as e:
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        print(f"Error en process_instrumental_only: {error_msg}")
        
        self.update_state(state='FAILURE', meta={
            'status': f'Error: {error_msg}',
            'error': error_msg,
            'traceback': traceback_str
        })
        raise Exception(error_msg)


def create_with_cancellation_check(video_path, enable_diarization=False, hf_token=None,
                                  source_type="upload", source_url=None, save_to_db=True):

    check_if_cancelled()
    
    #aqui igual poderia añadir mais chequeos nas etapas criticas, de momento chamo solo a funcion original
    return create(video_path, enable_diarization, hf_token, source_type, source_url, save_to_db)


def create_with_manual_lyrics_with_cancellation_check(video_path, manual_lyrics, language=None,
                                                     enable_diarization=False, hf_token=None,
                                                     source_type="upload", source_url=None, save_to_db=True):

    check_if_cancelled()
    
    #o mismo
    return create_with_manual_lyrics(video_path, manual_lyrics, language, enable_diarization, 
                                   hf_token, source_type, source_url, save_to_db)


def generate_instrumental_with_cancellation_check(video_path, source_type="upload", source_url=None, save_to_db=True):

    check_if_cancelled()
    return generate_instrumental(video_path, source_type, source_url, save_to_db)


def cleanup_partial_files(video_path):

    try:
        print(f"Limpando archivos parciales  {video_path}")
        
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        
        directories_to_clean = [
            "./input",
            "./output", 
            "./separated",
            "/data/input",
            "/data/output",
            "/data/separated"
        ]
        
        patterns = [
            f"*{base_name}*",
            f"karaoke_{base_name}*",
            f"karaoke_manual_{base_name}*",
            f"instrumental_{base_name}*",
            f"vocal_{base_name}*",
            f"*_whisperx.srt"
        ]
        
        import glob
        files_deleted = 0
        
        for directory in directories_to_clean:
            if os.path.exists(directory):
                for pattern in patterns:
                    files_to_delete = glob.glob(os.path.join(directory, pattern))
                    for file_path in files_to_delete:
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                files_deleted += 1
                        except Exception as e:
                            print(f" Erro eliminando {file_path}: {e}")
        
        print(f"Limpeza completada: {files_deleted} archivos eliminados")
        
    except Exception as e:
        print(f"Erro na limpeza: {e}")