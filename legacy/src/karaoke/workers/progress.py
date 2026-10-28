import logging

from celery import current_task

from karaoke.domain.errors import JobCancelled
from karaoke.workers.celery_app import active_processes, celery

logger = logging.getLogger(__name__)


class CeleryProgressReporter:
    def __init__(self, task) -> None:
        self._task = task

    def report(self, step: str, percent: int) -> None:
        self._task.update_state(
            state="PROGRESS",
            meta={"status": step, "current": percent, "total": 100},
        )

    def check_cancelled(self) -> None:
        task_id = current_task.request.id

        if task_id in active_processes:
            status = active_processes[task_id].get("status")
            if status in ("REVOKED", "CANCELLED"):
                raise JobCancelled("Task cancelled by user")

        if current_task.request.called_directly is False:
            try:
                result = celery.AsyncResult(task_id)
                if result.state == "REVOKED":
                    raise JobCancelled("Task revoked")
            except JobCancelled:
                raise
            except Exception:
                pass
