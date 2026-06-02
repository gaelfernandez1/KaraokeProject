"""Unit tests for the KaraokeJob / InstrumentalJob pipeline."""

from pathlib import Path

import pytest

from karaoke.domain.errors import (
    AlignmentError,
    AudioSeparationError,
    JobCancelled,
    PreparationError,
)
from karaoke.domain.pipeline import InstrumentalJob, JobConfig, KaraokeJob
from karaoke.domain.progress import NoopProgressReporter
from karaoke.domain.strategies import AutomaticAlignment, ManualLyricsAlignment

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_config(tmp_path: Path, task_id: str = "task-001") -> JobConfig:
    return JobConfig(
        video_path=tmp_path / "song.mp4",
        task_id=task_id,
        work_dir=tmp_path,
    )


def patch_prepare(monkeypatch, job_class, tmp_path: Path) -> None:
    """Patch _prepare so it populates minimal artifacts."""

    def _prepare(self):
        self._job_work_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts.original_video_path = tmp_path / "song.mp4"
        self.artifacts.video_path = tmp_path / "song.mp4"
        self.artifacts.audio_path = tmp_path / "song.mp3"

    monkeypatch.setattr(job_class, "_prepare", _prepare)


def patch_separate(monkeypatch, job_class, tmp_path: Path) -> None:
    def _separate(self):
        self.artifacts.vocal_path = tmp_path / "vocals.wav"
        self.artifacts.instrumental_path = tmp_path / "instrumental.wav"

    monkeypatch.setattr(job_class, "_separate", _separate)


# ---------------------------------------------------------------------------
# KaraokeJob orchestration
# ---------------------------------------------------------------------------


class TestKaraokeJobOrchestration:
    def test_run_calls_steps_in_order(self, monkeypatch, tmp_path):
        call_order: list[str] = []

        def _prepare(self):
            call_order.append("prepare")
            self._job_work_dir.mkdir(parents=True, exist_ok=True)
            self.artifacts.original_video_path = tmp_path / "song.mp4"
            self.artifacts.video_path = tmp_path / "song.mp4"
            self.artifacts.audio_path = tmp_path / "song.mp3"

        def _separate(self):
            call_order.append("separate")

        def _align(self):
            call_order.append("align")

        def _render(self):
            call_order.append("render")
            self.artifacts.karaoke_filename = "karaoke_small_song.mp4"

        def _persist(self):
            call_order.append("persist")

        monkeypatch.setattr(KaraokeJob, "_prepare", _prepare)
        monkeypatch.setattr(KaraokeJob, "_separate", _separate)
        monkeypatch.setattr(KaraokeJob, "_align", _align)
        monkeypatch.setattr(KaraokeJob, "_render", _render)
        monkeypatch.setattr(KaraokeJob, "_persist", _persist)

        config = make_config(tmp_path)
        job = KaraokeJob(
            config=config, strategy=AutomaticAlignment(), reporter=NoopProgressReporter()
        )
        result = job.run()

        assert call_order == ["prepare", "separate", "align", "render", "persist"]
        assert result == "karaoke_small_song.mp4"

    def test_work_dir_cleaned_up_on_success(self, monkeypatch, tmp_path):
        def _prepare(self):
            self._job_work_dir.mkdir(parents=True, exist_ok=True)
            (self._job_work_dir / "vocals.wav").write_bytes(b"data")
            self.artifacts.original_video_path = tmp_path / "song.mp4"
            self.artifacts.video_path = tmp_path / "song.mp4"
            self.artifacts.audio_path = tmp_path / "song.mp3"

        def _separate(self):
            pass

        def _align(self):
            pass

        def _render(self):
            self.artifacts.karaoke_filename = "karaoke_small_song.mp4"

        def _persist(self):
            pass

        monkeypatch.setattr(KaraokeJob, "_prepare", _prepare)
        monkeypatch.setattr(KaraokeJob, "_separate", _separate)
        monkeypatch.setattr(KaraokeJob, "_align", _align)
        monkeypatch.setattr(KaraokeJob, "_render", _render)
        monkeypatch.setattr(KaraokeJob, "_persist", _persist)

        config = make_config(tmp_path)
        job = KaraokeJob(
            config=config, strategy=AutomaticAlignment(), reporter=NoopProgressReporter()
        )
        job.run()

        assert not (tmp_path / "task-001").exists()

    def test_work_dir_cleaned_up_on_error(self, monkeypatch, tmp_path):
        def _prepare(self):
            self._job_work_dir.mkdir(parents=True, exist_ok=True)
            (self._job_work_dir / "temp.wav").write_bytes(b"data")
            self.artifacts.original_video_path = tmp_path / "song.mp4"
            self.artifacts.video_path = tmp_path / "song.mp4"
            self.artifacts.audio_path = tmp_path / "song.mp3"

        def _separate(self):
            raise AudioSeparationError("Demucs failed")

        monkeypatch.setattr(KaraokeJob, "_prepare", _prepare)
        monkeypatch.setattr(KaraokeJob, "_separate", _separate)

        config = make_config(tmp_path)
        job = KaraokeJob(
            config=config, strategy=AutomaticAlignment(), reporter=NoopProgressReporter()
        )
        with pytest.raises(AudioSeparationError):
            job.run()

        assert not (tmp_path / "task-001").exists()


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


class TestCancellation:
    @pytest.mark.parametrize(
        "failing_step",
        ["_prepare", "_separate", "_align", "_render", "_persist"],
    )
    def test_job_cancelled_propagates_from_any_step(self, monkeypatch, tmp_path, failing_step):
        def make_step(name: str):
            def step(self):
                if name == failing_step:
                    raise JobCancelled("user cancelled")
                if name == "_prepare":
                    self._job_work_dir.mkdir(parents=True, exist_ok=True)
                    self.artifacts.original_video_path = tmp_path / "song.mp4"
                    self.artifacts.video_path = tmp_path / "song.mp4"
                    self.artifacts.audio_path = tmp_path / "song.mp3"
                if name == "_render":
                    self.artifacts.karaoke_filename = "out.mp4"

            return step

        for step_name in ["_prepare", "_separate", "_align", "_render", "_persist"]:
            monkeypatch.setattr(KaraokeJob, step_name, make_step(step_name))

        config = make_config(tmp_path)
        job = KaraokeJob(
            config=config, strategy=AutomaticAlignment(), reporter=NoopProgressReporter()
        )
        with pytest.raises(JobCancelled):
            job.run()

        assert not (tmp_path / "task-001").exists()

    def test_reporter_check_cancelled_raises_job_cancelled(self, monkeypatch, tmp_path):
        class CancellingReporter:
            call_count = 0

            def report(self, step: str, percent: int) -> None:
                pass

            def check_cancelled(self) -> None:
                self.call_count += 1
                raise JobCancelled("cancelled by test")

        cancelling_reporter = CancellingReporter()

        def _prepare(self):
            self._job_work_dir.mkdir(parents=True, exist_ok=True)
            self.artifacts.original_video_path = tmp_path / "song.mp4"
            self.artifacts.video_path = tmp_path / "song.mp4"
            self.artifacts.audio_path = tmp_path / "song.mp3"

        def _separate(self):
            self.artifacts.vocal_path = tmp_path / "vocals.wav"
            self.artifacts.instrumental_path = tmp_path / "instrumental.wav"

        monkeypatch.setattr(KaraokeJob, "_prepare", _prepare)
        monkeypatch.setattr(KaraokeJob, "_separate", _separate)

        config = make_config(tmp_path)
        job = KaraokeJob(config=config, strategy=AutomaticAlignment(), reporter=cancelling_reporter)
        with pytest.raises(JobCancelled):
            job.run()


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


class TestPipelineErrors:
    def test_preparation_error_on_missing_audio(self, monkeypatch, tmp_path):
        monkeypatch.setattr("karaoke.infra.video_processing.normalize_video", lambda p: p)
        monkeypatch.setattr("karaoke.infra.audio_processing.video_to_mp3", lambda p: "")

        config = make_config(tmp_path)
        job = KaraokeJob(
            config=config, strategy=AutomaticAlignment(), reporter=NoopProgressReporter()
        )
        with pytest.raises(PreparationError):
            job.run()

    def test_audio_separation_error_on_demucs_failure(self, monkeypatch, tmp_path):
        monkeypatch.setattr("karaoke.infra.video_processing.normalize_video", lambda p: p)
        monkeypatch.setattr(
            "karaoke.infra.audio_processing.video_to_mp3", lambda p: str(tmp_path / "audio.mp3")
        )
        monkeypatch.setattr("karaoke.infra.audio_processing.separate_stems_cli", lambda p: ("", ""))

        config = make_config(tmp_path)
        job = KaraokeJob(
            config=config, strategy=AutomaticAlignment(), reporter=NoopProgressReporter()
        )
        with pytest.raises(AudioSeparationError):
            job.run()

    def test_alignment_error_on_whisperx_no_content(self, monkeypatch, tmp_path):
        patch_prepare(monkeypatch, KaraokeJob, tmp_path)

        def _separate(self):
            self.artifacts.vocal_path = tmp_path / "vocals.wav"
            self.artifacts.instrumental_path = tmp_path / "instrumental.wav"

        monkeypatch.setattr(KaraokeJob, "_separate", _separate)
        monkeypatch.setattr(
            "karaoke.infra.audio_processing.transcribe_with_faster_whisper",
            lambda path, model: "hello",
        )
        monkeypatch.setattr(
            "karaoke.infra.whisperx_client.call_whisperx_endpoint_manual",
            lambda *a, **kw: None,
        )

        config = make_config(tmp_path)
        job = KaraokeJob(
            config=config, strategy=AutomaticAlignment(), reporter=NoopProgressReporter()
        )
        with pytest.raises(AlignmentError):
            job.run()


# ---------------------------------------------------------------------------
# Strategy differences
# ---------------------------------------------------------------------------


class TestAlignmentStrategies:
    def test_automatic_alignment_calls_transcription(self, monkeypatch):
        transcription_calls: list[str] = []

        monkeypatch.setattr(
            "karaoke.infra.audio_processing.transcribe_with_faster_whisper",
            lambda path, model: transcription_calls.append(path) or "hello world",
        )
        monkeypatch.setattr(
            "karaoke.infra.whisperx_client.call_whisperx_endpoint_manual",
            lambda *a, **kw: {"srt_content": "1\n00:00:00,000 --> 00:00:01,000\nhello\n\n"},
        )

        config = make_config(Path("/tmp"), task_id="t")
        strategy = AutomaticAlignment()
        result = strategy.align(Path("/fake/vocals.wav"), Path("/tmp/t"), config)

        assert len(transcription_calls) == 1
        assert "1\n00:00:00" in result

    def test_manual_alignment_skips_transcription(self, monkeypatch):
        transcription_calls: list = []

        monkeypatch.setattr(
            "karaoke.infra.audio_processing.transcribe_with_faster_whisper",
            lambda *a: transcription_calls.append("called") or "",
        )
        monkeypatch.setattr(
            "karaoke.infra.whisperx_client.call_whisperx_endpoint_manual",
            lambda *a, **kw: {"srt_content": "1\n00:00:00,000 --> 00:00:01,000\nhello\n\n"},
        )

        config = make_config(Path("/tmp"), task_id="t")
        strategy = ManualLyricsAlignment(lyrics="hello world")
        result = strategy.align(Path("/fake/vocals.wav"), Path("/tmp/t"), config)

        assert transcription_calls == []
        assert "1\n00:00:00" in result

    def test_automatic_raises_on_empty_transcription(self, monkeypatch):
        monkeypatch.setattr(
            "karaoke.infra.audio_processing.transcribe_with_faster_whisper",
            lambda *a: "",
        )

        config = make_config(Path("/tmp"), task_id="t")
        strategy = AutomaticAlignment()
        with pytest.raises(AlignmentError, match="empty transcription"):
            strategy.align(Path("/fake/vocals.wav"), Path("/tmp/t"), config)

    def test_automatic_raises_when_whisperx_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            "karaoke.infra.audio_processing.transcribe_with_faster_whisper",
            lambda *a: "lyrics",
        )
        monkeypatch.setattr(
            "karaoke.infra.whisperx_client.call_whisperx_endpoint_manual",
            lambda *a, **kw: None,
        )

        config = make_config(Path("/tmp"), task_id="t")
        strategy = AutomaticAlignment()
        with pytest.raises(AlignmentError, match="no srt_content"):
            strategy.align(Path("/fake/vocals.wav"), Path("/tmp/t"), config)

    def test_automatic_captures_detected_language(self, monkeypatch):
        monkeypatch.setattr(
            "karaoke.infra.audio_processing.transcribe_with_faster_whisper",
            lambda path, model: "hello world",
        )
        monkeypatch.setattr(
            "karaoke.infra.whisperx_client.call_whisperx_endpoint_manual",
            lambda *a, **kw: {
                "srt_content": "1\n00:00:00,000 --> 00:00:01,000\nhello\n\n",
                "detected_language": "gl",
            },
        )

        config = make_config(Path("/tmp"), task_id="t")
        strategy = AutomaticAlignment()
        strategy.align(Path("/fake/vocals.wav"), Path("/tmp/t"), config)

        assert strategy.detected_language == "gl"

    def test_manual_captures_detected_language(self, monkeypatch):
        monkeypatch.setattr(
            "karaoke.infra.whisperx_client.call_whisperx_endpoint_manual",
            lambda *a, **kw: {
                "srt_content": "1\n00:00:00,000 --> 00:00:01,000\nhello\n\n",
                "detected_language": "pt",
            },
        )

        config = make_config(Path("/tmp"), task_id="t")
        strategy = ManualLyricsAlignment(lyrics="hello world")
        strategy.align(Path("/fake/vocals.wav"), Path("/tmp/t"), config)

        assert strategy.detected_language == "pt"

    def test_detected_language_absent_defaults_to_none(self, monkeypatch):
        monkeypatch.setattr(
            "karaoke.infra.audio_processing.transcribe_with_faster_whisper",
            lambda path, model: "hi",
        )
        monkeypatch.setattr(
            "karaoke.infra.whisperx_client.call_whisperx_endpoint_manual",
            lambda *a, **kw: {"srt_content": "1\n00:00:00,000 --> 00:00:01,000\nhi\n\n"},
        )

        config = make_config(Path("/tmp"), task_id="t")
        strategy = AutomaticAlignment()
        strategy.align(Path("/fake/vocals.wav"), Path("/tmp/t"), config)

        assert strategy.detected_language is None

    def test_manual_uses_normalized_lyrics_for_grouping(self, sample_srt_path):
        from karaoke.domain.srt_processing import parse_word_srt

        strategy = ManualLyricsAlignment(lyrics="Hello world\nGoodbye")
        segments = parse_word_srt(sample_srt_path)
        groups = strategy.group_segments(segments)
        assert isinstance(groups, list)

    def test_automatic_groups_by_pause(self, sample_srt_path):
        from karaoke.domain.srt_processing import parse_word_srt

        strategy = AutomaticAlignment()
        segments = parse_word_srt(sample_srt_path)
        groups = strategy.group_segments(segments)
        assert isinstance(groups, list)
        assert len(groups) >= 1


# ---------------------------------------------------------------------------
# InstrumentalJob
# ---------------------------------------------------------------------------


class TestInstrumentalJob:
    def _make_job(self, tmp_path: Path) -> InstrumentalJob:
        config = make_config(tmp_path)
        return InstrumentalJob(config=config, reporter=NoopProgressReporter())

    def test_run_does_not_have_align_or_render(self):
        assert not hasattr(InstrumentalJob, "_align")
        assert not hasattr(InstrumentalJob, "_render")

    def test_run_calls_prepare_separate_persist(self, monkeypatch, tmp_path):
        call_order: list[str] = []

        def _prepare(self):
            call_order.append("prepare")
            self._job_work_dir.mkdir(parents=True, exist_ok=True)
            self.artifacts.original_video_path = tmp_path / "song.mp4"
            self.artifacts.video_path = tmp_path / "song.mp4"
            self.artifacts.audio_path = tmp_path / "song.mp3"

        def _separate(self):
            call_order.append("separate")

        def _persist(self):
            call_order.append("persist")
            self.artifacts.karaoke_filename = "instrumental_song.wav"

        monkeypatch.setattr(InstrumentalJob, "_prepare", _prepare)
        monkeypatch.setattr(InstrumentalJob, "_separate", _separate)
        monkeypatch.setattr(InstrumentalJob, "_persist", _persist)

        job = self._make_job(tmp_path)
        result = job.run()

        assert call_order == ["prepare", "separate", "persist"]
        assert result == "instrumental_song.wav"

    def test_work_dir_cleaned_up(self, monkeypatch, tmp_path):
        def _prepare(self):
            self._job_work_dir.mkdir(parents=True, exist_ok=True)
            (self._job_work_dir / "stems.wav").write_bytes(b"data")
            self.artifacts.original_video_path = tmp_path / "song.mp4"
            self.artifacts.video_path = tmp_path / "song.mp4"
            self.artifacts.audio_path = tmp_path / "song.mp3"

        def _separate(self):
            raise AudioSeparationError("test error")

        monkeypatch.setattr(InstrumentalJob, "_prepare", _prepare)
        monkeypatch.setattr(InstrumentalJob, "_separate", _separate)

        job = self._make_job(tmp_path)
        with pytest.raises(AudioSeparationError):
            job.run()

        assert not (tmp_path / "task-001").exists()

    @pytest.mark.parametrize(
        "input_name,expected_prefix",
        [
            ("song.mp4", "instrumental_song.wav"),
            ("track.mp3", "instrumental_track.wav"),
            ("audio", "instrumental_audio.wav"),
        ],
    )
    def test_output_filename_logic(self, monkeypatch, tmp_path, input_name, expected_prefix):
        instrumental_file = tmp_path / "instrumental.wav"
        instrumental_file.write_bytes(b"audio data")
        output_dir = tmp_path / "output"

        def _prepare(self):
            self._job_work_dir.mkdir(parents=True, exist_ok=True)
            self.artifacts.original_video_path = tmp_path / input_name
            self.artifacts.video_path = tmp_path / input_name
            self.artifacts.audio_path = tmp_path / "audio.mp3"

        def _separate(self):
            self.artifacts.instrumental_path = instrumental_file

        monkeypatch.setattr(InstrumentalJob, "_prepare", _prepare)
        monkeypatch.setattr(InstrumentalJob, "_separate", _separate)
        monkeypatch.setattr("karaoke.domain.pipeline.save_song", lambda *a, **k: 1)

        config = JobConfig(
            video_path=tmp_path / input_name,
            task_id="fname-test",
            output_dir=output_dir,
            work_dir=tmp_path,
            save_to_db=False,
        )
        job = InstrumentalJob(config=config, reporter=NoopProgressReporter())
        result = job.run()
        assert result == expected_prefix


# ---------------------------------------------------------------------------
# Owner attribution
# ---------------------------------------------------------------------------


class TestPersistUserId:
    def test_persist_attaches_user_id_to_saved_song(self, monkeypatch, tmp_path):
        captured: dict = {}
        monkeypatch.setattr(
            "karaoke.domain.pipeline.save_song",
            lambda session, metadata: captured.update(metadata) or 1,
        )
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "karaoke_small_song.mp4").write_bytes(b"video")

        config = JobConfig(
            video_path=tmp_path / "song.mp4",
            task_id="persist-1",
            output_dir=output_dir,
            work_dir=tmp_path,
            user_id="user-xyz",
        )
        job = KaraokeJob(
            config=config, strategy=AutomaticAlignment(), reporter=NoopProgressReporter()
        )
        job.artifacts.karaoke_filename = "karaoke_small_song.mp4"
        job.artifacts.video_path = tmp_path / "song.mp4"

        job._persist()

        assert captured["user_id"] == "user-xyz"


# ---------------------------------------------------------------------------
# Syllabification language resolution
# ---------------------------------------------------------------------------


class TestLanguageResolution:
    class _FakeStrategy:
        is_manual_lyrics = False

        def __init__(self, detected=None, language=None):
            self.detected_language = detected
            self.language = language

        def align(self, vocal_path, work_dir, config):
            return "1\n00:00:00,000 --> 00:00:01,000\nhola\n\n"

        def group_segments(self, segments):
            return [{"start": 0.0, "end": 1.0, "line_text": "hola", "words": []}]

    def _resolve(self, tmp_path, strategy, config_language=None):
        config = JobConfig(
            video_path=tmp_path / "song.mp4",
            task_id="lang",
            work_dir=tmp_path,
            language=config_language,
        )
        job = KaraokeJob(config=config, strategy=strategy, reporter=NoopProgressReporter())
        job._job_work_dir.mkdir(parents=True, exist_ok=True)
        job.artifacts.vocal_path = tmp_path / "vocals.wav"
        job._align()
        return job._language

    def test_uses_detected_language(self, tmp_path):
        assert self._resolve(tmp_path, self._FakeStrategy(detected="gl")) == "gl"

    def test_config_language_overrides_detected(self, tmp_path):
        assert self._resolve(tmp_path, self._FakeStrategy(detected="gl"), "en") == "en"

    def test_falls_back_to_strategy_language(self, tmp_path):
        assert self._resolve(tmp_path, self._FakeStrategy(language="ca")) == "ca"

    def test_defaults_to_es_when_nothing_known(self, tmp_path):
        assert self._resolve(tmp_path, self._FakeStrategy()) == "es"
