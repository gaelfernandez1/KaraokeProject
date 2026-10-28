"""Modal GPU worker for the karaoke pipeline.

Deploy with:  modal deploy modal/karaoke_worker.py
Run one-off:  modal run modal/karaoke_worker.py::run_karaoke_job  (needs args)

The Celery task in karaoke.workers.celery_tasks dispatches to this function by
name (modal.Function.from_name) when Settings.modal_dispatch is true; it never
imports this module, so the top-level ``modal`` name here can't shadow the client.

The image mirrors Dockerfile.worker's system deps. CUDA/ffmpeg/av pinning was
painful there (see its comments) and will likely need a round or two of
`modal deploy` iteration here too — torch==2.3.0 pulls its default CUDA wheel,
which Modal's T4 drivers run.
"""

import modal

app = modal.App("karaoke-gpu")

gpu_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install(
        "git",
        "ffmpeg",
        "imagemagick",
        "libpangocairo-1.0-0",
        "libpangoft2-1.0-0",
        "libmagickwand-dev",
        "build-essential",
        "pkg-config",
    )
    # MoviePy's TextClip shells out to ImageMagick, whose default policy.xml blocks
    # the @ path it uses. Same patch as Dockerfile.worker.
    .run_commands(
        'sed -i \'s|<policy domain="path" rights="none" pattern="@\\*"/>|'
        "<!-- patched for moviepy -->|' /etc/ImageMagick-6/policy.xml || true"
    )
    # Install the worker dependency set straight from pyproject so it never drifts
    # from the local images. The original spec's literal .pip_install(...) would
    # duplicate the whole list and rot.
    .pip_install_from_pyproject("pyproject.toml", optional_dependencies=["worker"])
    # Ship the karaoke package itself — the deps above don't include our source.
    .add_local_python_source("karaoke")
)


@app.function(
    image=gpu_image,
    gpu="T4",
    timeout=600,
    secrets=[modal.Secret.from_name("karaoke-secrets")],
)
def run_karaoke_job(task_id: str, job_config_dict: dict) -> str:
    """Run one karaoke job on GPU and return the R2 storage key of the output.

    Runtime prerequisites when MODAL_DISPATCH is on (see docs/05-runbook.md):
      - karaoke-secrets must carry STORAGE_BACKEND=r2 and the R2_* credentials,
        DATABASE_URL (Neon), FLASK_SECRET_KEY, and WHISPERX_SERVICE_URL pointing
        at a WhisperX endpoint reachable from Modal.
      - youtube jobs are self-contained (re-downloaded here); upload-sourced jobs
        need their input staged in R2 first. See the TODO below.
    """
    from karaoke.config import Settings
    from karaoke.domain.pipeline import JobConfig, KaraokeJob
    from karaoke.domain.strategies import AutomaticAlignment, ManualLyricsAlignment
    from karaoke.infra.storage import get_storage

    settings = Settings()
    storage = get_storage(settings)  # R2 from the Modal secret

    # A local file path doesn't survive the network hop. youtube jobs carry a
    # source_url we can re-fetch here; uploads would need R2 staging first.
    # TODO(F13+): stage uploaded inputs in R2 and pull them here before running.
    if job_config_dict.get("source_type") == "youtube" and job_config_dict.get("source_url"):
        from karaoke.infra.youtube import download_youtube

        job_config_dict = {
            **job_config_dict,
            "video_path": download_youtube(job_config_dict["source_url"]),
        }

    config = JobConfig.from_transport_dict(job_config_dict, storage=storage)

    strategy_spec = job_config_dict.get("strategy", {})
    if strategy_spec.get("kind") == "manual":
        strategy = ManualLyricsAlignment(
            lyrics=strategy_spec["lyrics"], language=strategy_spec.get("language")
        )
    else:
        strategy = AutomaticAlignment()

    job = KaraokeJob(config=config, strategy=strategy)
    filename = job.run()
    return f"karaoke/{task_id}/{filename}"
