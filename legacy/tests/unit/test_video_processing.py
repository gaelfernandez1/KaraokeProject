import json
from unittest.mock import MagicMock

import karaoke.infra.video_processing as vp


def _ffprobe_result(codec_name: str, codec_type: str = "video") -> MagicMock:
    payload = {
        "streams": [
            {"codec_type": codec_type, "codec_name": codec_name, "width": 1280, "height": 720}
        ]
    }
    mock = MagicMock()
    mock.stdout = json.dumps(payload)
    return mock


class TestGetVideoCodec:
    def test_returns_h264(self, monkeypatch):
        monkeypatch.setattr(vp.subprocess, "run", lambda *a, **kw: _ffprobe_result("h264"))
        assert vp.get_video_codec("fake.mp4") == "h264"

    def test_returns_av01(self, monkeypatch):
        monkeypatch.setattr(vp.subprocess, "run", lambda *a, **kw: _ffprobe_result("av01"))
        assert vp.get_video_codec("fake.mp4") == "av01"

    def test_returns_none_on_subprocess_error(self, monkeypatch):
        monkeypatch.setattr(vp.subprocess, "run", MagicMock(side_effect=Exception("fail")))
        assert vp.get_video_codec("fake.mp4") is None

    def test_returns_none_when_no_video_stream(self, monkeypatch):
        payload = {"streams": [{"codec_type": "audio", "codec_name": "aac"}]}
        mock = MagicMock()
        mock.stdout = json.dumps(payload)
        monkeypatch.setattr(vp.subprocess, "run", lambda *a, **kw: mock)
        assert vp.get_video_codec("fake.mp4") is None

    def test_returns_none_on_empty_streams(self, monkeypatch):
        mock = MagicMock()
        mock.stdout = json.dumps({"streams": []})
        monkeypatch.setattr(vp.subprocess, "run", lambda *a, **kw: mock)
        assert vp.get_video_codec("fake.mp4") is None


class TestNeedsReencoding:
    def test_h264_does_not_need_reencoding(self, monkeypatch):
        monkeypatch.setattr(vp.subprocess, "run", lambda *a, **kw: _ffprobe_result("h264"))
        assert vp.needs_reencoding("fake.mp4") is False

    def test_av01_needs_reencoding(self, monkeypatch):
        monkeypatch.setattr(vp.subprocess, "run", lambda *a, **kw: _ffprobe_result("av01"))
        assert vp.needs_reencoding("fake.mp4") is True

    def test_hevc_needs_reencoding(self, monkeypatch):
        monkeypatch.setattr(vp.subprocess, "run", lambda *a, **kw: _ffprobe_result("hevc"))
        assert vp.needs_reencoding("fake.mp4") is True

    def test_vp9_needs_reencoding(self, monkeypatch):
        monkeypatch.setattr(vp.subprocess, "run", lambda *a, **kw: _ffprobe_result("vp9"))
        assert vp.needs_reencoding("fake.mp4") is True

    def test_none_codec_defaults_to_needs_reencoding(self, monkeypatch):
        # ffprobe failure → codec is None → safe default is True (re-encode)
        monkeypatch.setattr(vp.subprocess, "run", MagicMock(side_effect=Exception("fail")))
        assert vp.needs_reencoding("fake.mp4") is True

    def test_mpeg4_does_not_need_reencoding(self, monkeypatch):
        monkeypatch.setattr(vp.subprocess, "run", lambda *a, **kw: _ffprobe_result("mpeg4"))
        assert vp.needs_reencoding("fake.mp4") is False
