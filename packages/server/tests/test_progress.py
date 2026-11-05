from karaoke_server.jobs.progress import DEFAULTS, ENGINE_STAGE, Estimator, plan_for
from karaoke_server.jobs.store import JobRecord


def record(**changes: object) -> JobRecord:
    base = JobRecord.new("j1", "make", "Song", {"language": "gl", "lyrics": "la la"}, now=100.0)
    for key, value in changes.items():
        setattr(base, key, value)
    return base


def test_engine_steps_map_to_the_web_stages() -> None:
    assert ENGINE_STAGE == {
        "decode": "separate",
        "separate": "separate",
        "transcribe": "transcribe",
        "align": "align",
        "encode": "audio",
    }


def test_plan_skips_transcription_with_lyrics_and_adds_download_for_links() -> None:
    assert plan_for(record()) == ["separate", "align", "audio"]
    no_lyrics = record(request={"language": "gl", "url": "https://x"}, with_lyrics=False)
    assert plan_for(no_lyrics) == ["download", "separate", "transcribe", "align", "audio"]
    assert plan_for(record(kind="export")) == ["video"]


def test_defaults_scale_with_the_song() -> None:
    estimator = Estimator(history=lambda stage: [])
    short = estimator.expected("separate", 60)
    long = estimator.expected("separate", 240)
    assert long > short > DEFAULTS["separate"][0]


def test_estimator_uses_history_median() -> None:
    estimator = Estimator(history=lambda stage: [0.5, 0.1, 0.3] if stage == "align" else [])
    assert estimator.expected("align", 100) == 30.0


def test_progress_never_reaches_one_before_done() -> None:
    estimator = Estimator(history=lambda stage: [])
    assert estimator.stage_progress("separate", 10_000, 240) == 0.97
    assert 0 < estimator.stage_progress("separate", 5, 240) < 0.5


def test_overall_and_eta() -> None:
    estimator = Estimator(history=lambda stage: [])
    queued = record(duration=240.0)
    assert estimator.overall(queued, now=100.0) == 0.0
    assert estimator.eta(queued, now=100.0) is None
    running = record(stage="align", stage_started=100.0, duration=240.0)
    overall = estimator.overall(running, now=105.0)
    assert overall is not None
    separate = estimator.expected("separate", 240)
    align = estimator.expected("align", 240)
    audio = estimator.expected("audio", 240)
    assert abs(overall - (separate + 5) / (separate + align + audio)) < 1e-6
    eta = estimator.eta(running, now=105.0)
    assert eta is not None
    assert abs(eta - (align - 5 + audio)) < 1e-6
    assert estimator.overall(record(stage="done"), now=0) == 1.0
    assert estimator.overall(record(stage="error"), now=0) is None
