import logging
from pathlib import Path

from karaoke.config import Settings
from karaoke.domain.errors import JobCancelled, PipelineError
from karaoke.domain.pipeline import InstrumentalJob, JobConfig, KaraokeJob
from karaoke.domain.strategies import AutomaticAlignment, ManualLyricsAlignment
from karaoke.infra.storage import get_storage
from karaoke.workers.celery_app import celery
from karaoke.workers.progress import CeleryProgressReporter

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="process_automatic_karaoke")
def process_automatic_karaoke(
    self,
    video_path: str,
    enable_diarization: bool = False,
    hf_token: str | None = None,
    whisper_model: str = "small",
    source_type: str = "upload",
    source_url: str | None = None,
    save_to_db: bool = True,
    user_id: str | None = None,
):
    task_id = self.request.id
    reporter = CeleryProgressReporter(self)
    reporter.report("Iniciando procesamento automático...", 0)

    if source_type == "youtube":
        from karaoke.infra.youtube import download_youtube  # noqa: PLC0415

        reporter.report("Descargando vídeo de YouTube...", 2)
        video_path = download_youtube(source_url)

    config = JobConfig(
        video_path=Path(video_path),
        task_id=task_id,
        source_type=source_type,
        source_url=source_url,
        enable_diarization=enable_diarization,
        hf_token=hf_token,
        whisper_model=whisper_model,
        save_to_db=save_to_db,
        user_id=user_id,
        work_dir=Path("/data"),
        storage=get_storage(Settings()),
    )
    job = KaraokeJob(config=config, strategy=AutomaticAlignment(), reporter=reporter)

    try:
        filename = job.run()
        return {"status": "completed", "result": filename, "message": "Karaoke automático xerado"}
    except JobCancelled:
        self.update_state(state="REVOKED", meta={"status": "Procesamento cancelado"})
        raise
    except PipelineError as e:
        logger.error(f"Pipeline failed [{task_id}]: {e}")
        raise


@celery.task(bind=True, name="process_manual_lyrics_karaoke")
def process_manual_lyrics_karaoke(
    self,
    video_path: str,
    manual_lyrics: str,
    language: str | None = None,
    enable_diarization: bool = False,
    hf_token: str | None = None,
    whisper_model: str = "small",
    source_type: str = "upload",
    source_url: str | None = None,
    save_to_db: bool = True,
    user_id: str | None = None,
):
    task_id = self.request.id
    reporter = CeleryProgressReporter(self)
    reporter.report("Iniciando procesamento con letras manuais...", 0)

    if source_type == "youtube":
        from karaoke.infra.youtube import download_youtube  # noqa: PLC0415

        reporter.report("Descargando vídeo de YouTube...", 2)
        video_path = download_youtube(source_url)

    config = JobConfig(
        video_path=Path(video_path),
        task_id=task_id,
        source_type=source_type,
        source_url=source_url,
        enable_diarization=enable_diarization,
        hf_token=hf_token,
        whisper_model=whisper_model,
        save_to_db=save_to_db,
        user_id=user_id,
        work_dir=Path("/data"),
        storage=get_storage(Settings()),
    )
    strategy = ManualLyricsAlignment(lyrics=manual_lyrics, language=language)
    job = KaraokeJob(config=config, strategy=strategy, reporter=reporter)

    try:
        filename = job.run()
        return {
            "status": "completed",
            "result": filename,
            "message": "Karaoke con letras manuais xerado",
        }
    except JobCancelled:
        self.update_state(state="REVOKED", meta={"status": "Procesamento cancelado"})
        raise
    except PipelineError as e:
        logger.error(f"Pipeline failed [{task_id}]: {e}")
        raise


@celery.task(bind=True, name="process_instrumental_only")
def process_instrumental_only(
    self,
    video_path: str,
    source_type: str = "upload",
    source_url: str | None = None,
    save_to_db: bool = True,
    user_id: str | None = None,
):
    task_id = self.request.id
    reporter = CeleryProgressReporter(self)
    reporter.report("Xerando instrumental...", 0)

    if source_type == "youtube":
        from karaoke.infra.youtube import download_youtube  # noqa: PLC0415

        reporter.report("Descargando vídeo de YouTube...", 2)
        video_path = download_youtube(source_url)

    config = JobConfig(
        video_path=Path(video_path),
        task_id=task_id,
        source_type=source_type,
        source_url=source_url,
        save_to_db=save_to_db,
        user_id=user_id,
        work_dir=Path("/data"),
        storage=get_storage(Settings()),
    )
    job = InstrumentalJob(config=config, reporter=reporter)

    try:
        filename = job.run()
        return {"status": "completed", "result": filename, "message": "Instrumental xerada"}
    except JobCancelled:
        self.update_state(state="REVOKED", meta={"status": "Procesamento cancelado"})
        raise
    except PipelineError as e:
        logger.error(f"Pipeline failed [{task_id}]: {e}")
        raise
