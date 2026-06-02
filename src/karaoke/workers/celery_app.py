import logging
import os
import time

from celery import Celery
from celery.signals import task_failure, task_postrun, task_prerun, task_revoked

from karaoke.logging_config import _task_id_var

logger = logging.getLogger(__name__)


def make_celery():
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

    celery = Celery(
        "karaoke_tasks",
        broker=broker_url,
        backend=result_backend,
        include=["karaoke.workers.celery_tasks"],
    )

    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,
        worker_prefetch_multiplier=1,
    )

    return celery


celery = make_celery()

active_processes = {}


@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    _task_id_var.set(task_id)
    logger.info(f"Iniciando tarefa {task_id}: {task.name}", extra={"task_id": task_id})
    active_processes[task_id] = {"pid": os.getpid(), "started_at": time.time(), "status": "RUNNING"}


@task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    logger.info(f"Tarefa completada {task_id}", extra={"task_id": task_id})
    if task_id in active_processes:
        active_processes[task_id]["status"] = "COMPLETED"
        del active_processes[task_id]
    _task_id_var.set("")


@task_failure.connect
def task_failure_handler(task_id, exception, einfo, *args, **kwargs):
    logger.error(f"Tarefa fallida (celery) {task_id}: {exception}", extra={"task_id": task_id})
    if task_id in active_processes:
        active_processes[task_id]["status"] = "FAILED"
        del active_processes[task_id]
    _task_id_var.set("")


@task_revoked.connect
def task_revoked_handler(task_id, *args, **kwargs):
    # psutil lives in the worker image only; this handler only ever fires there.
    import psutil  # noqa: PLC0415

    logger.info(f"Tarefa cancelada {task_id}", extra={"task_id": task_id})
    if task_id in active_processes:
        try:
            pid = active_processes[task_id]["pid"]
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)

            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass

            time.sleep(2)
            for child in children:
                try:
                    if child.is_running():
                        child.kill()
                except psutil.NoSuchProcess:
                    pass

        except Exception as e:
            logger.error(f"Error matando procesos: {e}", extra={"task_id": task_id})

        active_processes[task_id]["status"] = "REVOKED"
        del active_processes[task_id]
    _task_id_var.set("")


def cleanup_orphaned_processes():
    current_time = time.time()
    to_remove = []

    for task_id, process_info in active_processes.items():
        if current_time - process_info["started_at"] > 7200:
            to_remove.append(task_id)

    for task_id in to_remove:
        del active_processes[task_id]


if __name__ == "__main__":
    celery.start()
