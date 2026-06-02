"""Unit tests for the storage abstraction layer.

LocalStorage and R2Storage tests run without heavy dependencies (no pyphen, torch, etc.)
and pass locally. Pipeline integration tests require the worker container.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# R2Storage does a lazy `import boto3` inside __init__. Mock the module here so
# tests run without boto3 installed. Must happen before importing storage.
_boto3_mock = MagicMock()
sys.modules.setdefault("boto3", _boto3_mock)

from karaoke.infra.storage import LocalStorage, R2Storage, get_storage  # noqa: E402

# ---------------------------------------------------------------------------
# LocalStorage
# ---------------------------------------------------------------------------


class TestLocalStorage:
    def test_upload_copies_file_to_output_dir(self, tmp_path):
        src = tmp_path / "video.mp4"
        src.write_bytes(b"fake video data")
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        storage = LocalStorage(out_dir)
        storage.upload(src, "karaoke/task-abc/video.mp4")

        assert (out_dir / "video.mp4").exists()

    def test_upload_is_noop_when_source_equals_dest(self, tmp_path):
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        dest = out_dir / "video.mp4"
        dest.write_bytes(b"data")

        storage = LocalStorage(out_dir)
        storage.upload(dest, "karaoke/task-abc/video.mp4")

        assert dest.read_bytes() == b"data"

    def test_upload_returns_key(self, tmp_path):
        src = tmp_path / "video.mp4"
        src.write_bytes(b"data")
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        storage = LocalStorage(out_dir)
        key = "karaoke/task-abc/video.mp4"
        result = storage.upload(src, key)

        assert result == key

    def test_get_signed_url_uses_basename(self, tmp_path):
        storage = LocalStorage(tmp_path)
        url = storage.get_signed_url("karaoke/task-abc/video.mp4")

        assert url == "/serve_video/video.mp4"

    def test_get_signed_url_plain_filename(self, tmp_path):
        storage = LocalStorage(tmp_path)
        url = storage.get_signed_url("video.mp4")

        assert url == "/serve_video/video.mp4"

    def test_delete_removes_file(self, tmp_path):
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        f = out_dir / "video.mp4"
        f.write_bytes(b"data")

        storage = LocalStorage(out_dir)
        storage.delete("karaoke/task-abc/video.mp4")

        assert not f.exists()

    def test_delete_missing_file_is_noop(self, tmp_path):
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        storage = LocalStorage(out_dir)
        storage.delete("karaoke/task-abc/missing.mp4")

    def test_exists_true_when_file_present(self, tmp_path):
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        (out_dir / "video.mp4").write_bytes(b"data")

        storage = LocalStorage(out_dir)
        assert storage.exists("karaoke/task-abc/video.mp4") is True

    def test_exists_false_when_file_absent(self, tmp_path):
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        storage = LocalStorage(out_dir)
        assert storage.exists("karaoke/task-abc/missing.mp4") is False


# ---------------------------------------------------------------------------
# R2Storage
# ---------------------------------------------------------------------------


class TestR2Storage:
    def _make_storage(self) -> tuple["R2Storage", MagicMock]:
        mock_client = MagicMock()
        _boto3_mock.client.return_value = mock_client
        storage = R2Storage(
            account_id="acc123",
            bucket="karaoke-bucket",
            access_key_id="AKID",
            secret_access_key="SECRET",
        )
        return storage, mock_client

    def test_upload_calls_boto3_upload_file(self, tmp_path):
        fake_file = tmp_path / "video.mp4"
        fake_file.write_bytes(b"data")
        storage, mock_client = self._make_storage()

        storage.upload(fake_file, "karaoke/task-1/video.mp4")

        mock_client.upload_file.assert_called_once_with(
            str(fake_file), "karaoke-bucket", "karaoke/task-1/video.mp4"
        )

    def test_upload_returns_key(self, tmp_path):
        fake_file = tmp_path / "video.mp4"
        fake_file.write_bytes(b"data")
        storage, _ = self._make_storage()

        result = storage.upload(fake_file, "karaoke/task-1/video.mp4")

        assert result == "karaoke/task-1/video.mp4"

    def test_get_signed_url_calls_generate_presigned_url(self):
        storage, mock_client = self._make_storage()
        mock_client.generate_presigned_url.return_value = (
            "https://acc123.r2.cloudflarestorage.com/karaoke-bucket/karaoke/t/v.mp4"
            "?X-Amz-Expires=3600"
        )

        url = storage.get_signed_url("karaoke/task-1/video.mp4")

        mock_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "karaoke-bucket", "Key": "karaoke/task-1/video.mp4"},
            ExpiresIn=3600,
        )
        assert "r2.cloudflarestorage.com" in url

    def test_get_signed_url_respects_expires_in(self):
        storage, mock_client = self._make_storage()
        mock_client.generate_presigned_url.return_value = "https://example.com/signed"

        storage.get_signed_url("karaoke/task-1/video.mp4", expires_in=7200)

        _, kwargs = mock_client.generate_presigned_url.call_args
        assert kwargs["ExpiresIn"] == 7200

    def test_delete_calls_delete_object(self):
        storage, mock_client = self._make_storage()

        storage.delete("karaoke/task-1/video.mp4")

        mock_client.delete_object.assert_called_once_with(
            Bucket="karaoke-bucket", Key="karaoke/task-1/video.mp4"
        )

    def test_exists_true_on_head_object_success(self):
        storage, mock_client = self._make_storage()
        mock_client.head_object.return_value = {"ContentLength": 1024}

        assert storage.exists("karaoke/task-1/video.mp4") is True

    def test_exists_false_on_exception(self):
        storage, mock_client = self._make_storage()
        mock_client.head_object.side_effect = Exception("NoSuchKey")

        assert storage.exists("karaoke/task-1/video.mp4") is False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestStorageFactory:
    def test_get_storage_returns_local_by_default(self, tmp_path):
        class FakeSettings:
            storage_backend = "local"

        result = get_storage(FakeSettings())
        assert isinstance(result, LocalStorage)

    def test_get_storage_returns_r2_when_configured(self):
        class FakeSettings:
            storage_backend = "r2"
            r2_account_id = "acc123"
            r2_bucket = "bucket"
            r2_access_key_id = "key"
            r2_secret_access_key = "secret"

        mock_client = MagicMock()
        _boto3_mock.client.return_value = mock_client
        result = get_storage(FakeSettings())
        assert isinstance(result, R2Storage)


# ---------------------------------------------------------------------------
# Pipeline integration (requires worker deps — skipped locally without pyphen)
# ---------------------------------------------------------------------------

try:
    from karaoke.domain.pipeline import JobConfig, KaraokeJob  # noqa: E402
    from karaoke.domain.progress import NoopProgressReporter  # noqa: E402
    from karaoke.domain.strategies import AutomaticAlignment  # noqa: E402

    _pipeline_available = True
except ImportError:
    _pipeline_available = False


@pytest.mark.skipif(not _pipeline_available, reason="requires worker deps (pyphen, etc.)")
class TestPipelineStorageIntegration:
    def test_persist_calls_storage_upload(self, monkeypatch, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        video_file = output_dir / "karaoke_small_song.mp4"
        video_file.write_bytes(b"fake video")

        upload_calls: list[tuple[Path, str]] = []

        class TrackingStorage:
            def upload(self, local_path: Path, key: str) -> str:
                upload_calls.append((local_path, key))
                return key

            def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
                return f"/serve_video/{Path(key).name}"

            def delete(self, key: str) -> None:
                pass

            def exists(self, key: str) -> bool:
                return True

        def _prepare(self):
            self._job_work_dir.mkdir(parents=True, exist_ok=True)
            self.artifacts.original_video_path = tmp_path / "song.mp4"
            self.artifacts.video_path = tmp_path / "song.mp4"
            self.artifacts.audio_path = tmp_path / "song.mp3"

        def _separate(self):
            pass

        def _align(self):
            pass

        def _render(self):
            self.artifacts.karaoke_filename = "karaoke_small_song.mp4"

        monkeypatch.setattr(KaraokeJob, "_prepare", _prepare)
        monkeypatch.setattr(KaraokeJob, "_separate", _separate)
        monkeypatch.setattr(KaraokeJob, "_align", _align)
        monkeypatch.setattr(KaraokeJob, "_render", _render)
        monkeypatch.setattr("karaoke.infra.metadata_utils.get_video_duration", lambda p: 1.0)
        monkeypatch.setattr("karaoke.infra.metadata_utils.get_file_size", lambda p: 1024)
        monkeypatch.setattr("karaoke.domain.pipeline.save_song", lambda *a, **kw: 1)

        config = JobConfig(
            video_path=tmp_path / "song.mp4",
            task_id="task-abc",
            output_dir=output_dir,
            work_dir=tmp_path,
            storage=TrackingStorage(),
            save_to_db=True,
        )
        job = KaraokeJob(
            config=config, strategy=AutomaticAlignment(), reporter=NoopProgressReporter()
        )
        job.run()

        assert len(upload_calls) == 1
        local_path, key = upload_calls[0]
        assert key == "karaoke/task-abc/karaoke_small_song.mp4"
        assert local_path == output_dir / "karaoke_small_song.mp4"

    def test_persist_passes_storage_key_to_save_song(self, monkeypatch, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        video_file = output_dir / "karaoke_small_song.mp4"
        video_file.write_bytes(b"fake video")

        saved_metadata: list[dict] = []

        class DummyStorage:
            def upload(self, local_path: Path, key: str) -> str:
                return key

            def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
                return f"/serve_video/{Path(key).name}"

            def delete(self, key: str) -> None:
                pass

            def exists(self, key: str) -> bool:
                return True

        def fake_save_song(session, metadata):
            saved_metadata.append(metadata)
            return 1

        def _prepare(self):
            self._job_work_dir.mkdir(parents=True, exist_ok=True)
            self.artifacts.original_video_path = tmp_path / "song.mp4"
            self.artifacts.video_path = tmp_path / "song.mp4"
            self.artifacts.audio_path = tmp_path / "song.mp3"

        def _separate(self):
            pass

        def _align(self):
            pass

        def _render(self):
            self.artifacts.karaoke_filename = "karaoke_small_song.mp4"

        monkeypatch.setattr(KaraokeJob, "_prepare", _prepare)
        monkeypatch.setattr(KaraokeJob, "_separate", _separate)
        monkeypatch.setattr(KaraokeJob, "_align", _align)
        monkeypatch.setattr(KaraokeJob, "_render", _render)
        monkeypatch.setattr("karaoke.infra.metadata_utils.get_video_duration", lambda p: 1.0)
        monkeypatch.setattr("karaoke.infra.metadata_utils.get_file_size", lambda p: 1024)
        monkeypatch.setattr("karaoke.domain.pipeline.save_song", fake_save_song)

        config = JobConfig(
            video_path=tmp_path / "song.mp4",
            task_id="task-xyz",
            output_dir=output_dir,
            work_dir=tmp_path,
            storage=DummyStorage(),
            save_to_db=True,
        )
        job = KaraokeJob(
            config=config, strategy=AutomaticAlignment(), reporter=NoopProgressReporter()
        )
        job.run()

        assert len(saved_metadata) == 1
        assert saved_metadata[0]["storage_key"] == "karaoke/task-xyz/karaoke_small_song.mp4"
