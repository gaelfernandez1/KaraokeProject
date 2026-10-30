import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from karaoke_contracts import Line, Word, load_doc, validate_package
from karaoke_engine.align.lyrics import parse_lyrics, singer_id
from karaoke_engine.audio import AudioError
from karaoke_engine.cli import main
from karaoke_engine.make import make_package
from karaoke_engine.steps import Stems, Transcript, TranscriptSegment

pytestmark = pytest.mark.usefixtures("ffmpeg")


class CopySeparator:
    """Gives the mix as both stems, and remembers whether it was unloaded."""

    name = "copy"
    model = "copy-model"

    def __init__(self) -> None:
        self.unloaded = False

    def separate(self, audio: Path, work_dir: Path) -> Stems:
        work_dir.mkdir(parents=True, exist_ok=True)
        vocals, instrumental = work_dir / "vocals.wav", work_dir / "instrumental.wav"
        shutil.copy(audio, vocals)
        shutil.copy(audio, instrumental)
        return Stems(vocals=vocals, instrumental=instrumental)

    def unload(self) -> None:
        self.unloaded = True


class EvenAligner:
    """One line per non-empty lyric line, words one second apart."""

    name = "even"
    model_name = "even-model@1"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def align(self, vocals: Path, lyrics_lines: Sequence[str], language: str) -> list[Line]:
        return self.align_text(vocals, "\n".join(lyrics_lines), language)

    def align_text(self, vocals: Path, lyrics: str, language: str) -> list[Line]:
        if self.fail:
            raise RuntimeError("out of memory")
        lines, t = [], 0.5
        for i, parsed in enumerate(parse_lyrics(lyrics)):
            words = []
            for word in parsed.words:
                words.append(Word(text=word, start=t, end=t + 0.4, confidence=0.9))
                t += 0.5
            singer = singer_id(parsed.singer) if parsed.singer else None
            lines.append(Line(id=f"l{i + 1}", start=words[0].start, end=words[-1].end,
                              singer=singer, words=words))  # fmt: skip
        return lines


def _song(tmp_path: Path, seconds: int = 6) -> Path:
    song = tmp_path / "Unha canción.m4a"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=330:duration={seconds}",
         "-ac", "2", "-c:a", "aac", str(song)],
        check=True,
    )  # fmt: skip
    return song


def test_make_builds_a_valid_package(tmp_path: Path) -> None:
    separator = CopySeparator()
    out = tmp_path / "pkg"

    doc = make_package(
        _song(tmp_path), out, "gl", "Ola mar\nvai o vento\n",
        separator=separator, aligner=EvenAligner(), artist="Alguén",
    )  # fmt: skip

    assert validate_package(out) == []
    assert doc.title == "Unha canción"
    assert doc.id == "unha-cancion"
    assert doc.artist == "Alguén"
    assert [len(line.words) for line in doc.lines] == [2, 3]
    assert {p.name for p in out.iterdir()} >= {"karaoke.json", "instrumental.m4a", "vocals.m4a"}
    assert separator.unloaded
    assert not any(p.suffix == ".wav" for p in out.rglob("*"))


def test_make_records_provenance(tmp_path: Path) -> None:
    doc = make_package(
        _song(tmp_path), tmp_path / "pkg", "gl", "Ola mar\n",
        separator=CopySeparator(), aligner=EvenAligner(),
    )  # fmt: skip

    assert doc.provenance.lyrics_source == "user"
    assert doc.provenance.separation_model == "copy-model"
    assert doc.provenance.align_model == "even-model@1"
    assert doc.provenance.engine_version.startswith("karaoke-engine ")
    assert doc.language == "gl"


def test_make_notes_a_language_without_its_own_model(tmp_path: Path) -> None:
    doc = make_package(
        _song(tmp_path), tmp_path / "pkg", "eu", "Kaixo\n",
        separator=CopySeparator(), aligner=EvenAligner(),
    )  # fmt: skip

    [fallback] = doc.provenance.language_fallbacks
    assert (fallback.step, fallback.requested) == ("align", "eu")


def test_make_rejects_input_without_audio(tmp_path: Path) -> None:
    video = tmp_path / "silent.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=32x32:d=1",
         "-c:v", "mpeg4", str(video)],
        check=True,
    )  # fmt: skip

    with pytest.raises(AudioError, match="no audio"):
        make_package(video, tmp_path / "pkg", "gl", "Ola\n", separator=CopySeparator(),
                     aligner=EvenAligner())  # fmt: skip


def test_make_writes_karaoke_json_last(tmp_path: Path) -> None:
    out = tmp_path / "pkg"

    with pytest.raises(RuntimeError, match="out of memory"):
        make_package(_song(tmp_path), out, "gl", "Ola\n", separator=CopySeparator(),
                     aligner=EvenAligner(fail=True))  # fmt: skip

    assert not (out / "karaoke.json").exists()


class FakeTranscriber:
    name = "fake-asr"

    def __init__(self) -> None:
        self.unloaded = False

    def transcribe(self, vocals: Path, language: str) -> Transcript:
        segments = (TranscriptSegment(0.5, 1.5, "Ola mar."), TranscriptSegment(2.0, 3.0, "Vai"))
        return Transcript(language=language, segments=segments)

    def model_for_language(self, language: str) -> str:
        return "fake-asr-model@1"

    def unload(self) -> None:
        self.unloaded = True


def test_make_without_lyrics_transcribes(tmp_path: Path) -> None:
    transcriber = FakeTranscriber()

    doc = make_package(_song(tmp_path), tmp_path / "pkg", "gl", None, separator=CopySeparator(),
                       aligner=EvenAligner(), transcriber=transcriber)  # fmt: skip

    assert [" ".join(w.text for w in line.words) for line in doc.lines] == ["Ola mar.", "Vai"]
    assert doc.provenance.lyrics_source == "asr"
    assert doc.provenance.asr_model == "fake-asr-model@1"
    assert transcriber.unloaded


def test_cli_make_without_lyrics_transcribes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import karaoke_engine.make as make_module

    monkeypatch.setattr(make_module, "default_separator", CopySeparator)
    monkeypatch.setattr(make_module, "default_aligner", EvenAligner)
    monkeypatch.setattr(make_module.WhisperTranscriber, "prepare_for", lambda self, language: None)
    monkeypatch.setattr(
        make_module,
        "transcribe_in_child",
        lambda vocals, language: (FakeTranscriber().transcribe(vocals, language), "fake@1"),
    )
    out = tmp_path / "pkg"

    assert main(["make", str(_song(tmp_path)), "--out", str(out)]) == 0
    assert load_doc(out / "karaoke.json").provenance.lyrics_source == "asr"


def test_cli_make_reads_the_lyrics_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import karaoke_engine.make as make_module

    monkeypatch.setattr(make_module, "default_separator", CopySeparator)
    monkeypatch.setattr(make_module, "default_aligner", EvenAligner)
    lyrics = tmp_path / "letra.txt"
    lyrics.write_text("Ola mar\n", encoding="utf-8")
    out = tmp_path / "pkg"

    code = main(["make", str(_song(tmp_path)), "--lyrics", str(lyrics), "--out", str(out)])

    assert code == 0
    assert load_doc(out / "karaoke.json").lines[0].words[0].text == "Ola"


def test_make_lists_singers(tmp_path: Path) -> None:
    lyrics = "[Verso: Ana]\nOla mar\n[Estribillo: Brais]\nVai o vento\n[Final]\nAdeus\n"

    doc = make_package(_song(tmp_path), tmp_path / "pkg", "gl", lyrics,
                       separator=CopySeparator(), aligner=EvenAligner())  # fmt: skip

    names = {singer.id: singer.name for singer in doc.singers}
    assert names == {"s1": None, singer_id("Ana"): "Ana", singer_id("Brais"): "Brais"}
    assert [line.singer for line in doc.lines] == [singer_id("Ana"), singer_id("Brais"), "s1"]


def test_cli_make_looks_lyrics_up_when_asked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import karaoke_engine.cli as cli_module
    import karaoke_engine.make as make_module
    from karaoke_engine.lyrics_lookup import FoundLyrics

    monkeypatch.setattr(make_module, "default_separator", CopySeparator)
    monkeypatch.setattr(make_module, "default_aligner", EvenAligner)
    asked: list[tuple[str, str, float]] = []

    def fake_find(title: str, artist: str, duration: float) -> FoundLyrics:
        asked.append((title, artist, duration))
        return FoundLyrics(text="Ola mar\n", synced=None, source_id=7, duration=duration)

    monkeypatch.setattr(cli_module, "find_lyrics", fake_find)
    out = tmp_path / "pkg"

    code = main(["make", str(_song(tmp_path)), "--lrclib", "--title", "Canción", "--artist",
                 "Grupo", "--out", str(out)])  # fmt: skip

    assert code == 0
    assert asked
    assert asked[0][:2] == ("Canción", "Grupo")
    doc = load_doc(out / "karaoke.json")
    assert doc.provenance.lyrics_source == "lrclib"


def test_cli_lrclib_needs_title_and_artist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["make", str(_song(tmp_path)), "--lrclib", "--out", str(tmp_path / "p")]) == 2
    assert "--artist" in capsys.readouterr().err


def test_make_drops_an_old_document_first(tmp_path: Path) -> None:
    out = tmp_path / "pkg"
    make_package(_song(tmp_path), out, "gl", "Ola\n", separator=CopySeparator(),
                 aligner=EvenAligner())  # fmt: skip

    with pytest.raises(RuntimeError):
        make_package(_song(tmp_path), out, "gl", "Ola\n", separator=CopySeparator(),
                     aligner=EvenAligner(fail=True))  # fmt: skip

    assert not (out / "karaoke.json").exists()


def test_make_rejects_lyrics_without_sung_lines(tmp_path: Path) -> None:
    separator = CopySeparator()

    with pytest.raises(ValueError, match="no sung lines"):
        make_package(_song(tmp_path), tmp_path / "pkg", "gl", "[Estribillo]\n♪\n",
                     separator=separator, aligner=EvenAligner())  # fmt: skip


def test_make_rejects_a_bad_language_before_working(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="language"):
        make_package(_song(tmp_path), tmp_path / "pkg", "Galego", "Ola\n",
                     separator=CopySeparator(), aligner=EvenAligner())  # fmt: skip


def test_cli_reports_runtime_errors_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import karaoke_engine.make as make_module

    monkeypatch.setattr(make_module, "default_separator", CopySeparator)
    monkeypatch.setattr(make_module, "default_aligner", lambda **kw: EvenAligner(fail=True))
    lyrics = tmp_path / "letra.txt"
    lyrics.write_text("Ola\n", encoding="utf-8")

    code = main(
        ["make", str(_song(tmp_path)), "--lyrics", str(lyrics), "--out", str(tmp_path / "p")]
    )

    assert code == 1
    assert "out of memory" in capsys.readouterr().err


def test_cli_can_let_backing_vocals_overlap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import karaoke_engine.make as make_module

    seen: list[dict[str, object]] = []

    def aligner(**options: object) -> EvenAligner:
        seen.append(options)
        return EvenAligner()

    monkeypatch.setattr(make_module, "default_separator", CopySeparator)
    monkeypatch.setattr(make_module, "default_aligner", aligner)
    lyrics = tmp_path / "letra.txt"
    lyrics.write_text("Ola (mar)\n", encoding="utf-8")

    main(["make", str(_song(tmp_path)), "--lyrics", str(lyrics), "--out", str(tmp_path / "p"),
          "--overlap-backing"])  # fmt: skip

    assert seen == [{"overlap_backing": True}]


def test_make_reports_each_step(tmp_path: Path) -> None:
    steps: list[str] = []

    make_package(_song(tmp_path), tmp_path / "pkg", "gl", "Ola\n", separator=CopySeparator(),
                 aligner=EvenAligner(), progress=steps.append)  # fmt: skip

    assert steps == ["decode", "separate", "align", "encode"]


def test_the_default_transcriber_runs_in_a_child_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import karaoke_engine.make as make_module

    calls: list[tuple[str, str]] = []

    def fake_child(vocals: Path, language: str) -> tuple[Transcript, str]:
        calls.append((vocals.name, language))
        segments = (TranscriptSegment(0.5, 1.5, "Ola mar"),)
        return Transcript(language=language, segments=segments), "child-model@1"

    monkeypatch.setattr(make_module, "transcribe_in_child", fake_child)
    monkeypatch.setattr(make_module.WhisperTranscriber, "prepare_for", lambda self, language: None)

    doc = make_package(_song(tmp_path), tmp_path / "pkg", "gl", None, separator=CopySeparator(),
                       aligner=EvenAligner())  # fmt: skip

    assert calls == [("vocals.wav", "gl")]
    assert doc.provenance.asr_model == "child-model@1"


def test_make_keeps_the_video_as_background_and_a_cover(tmp_path: Path) -> None:
    clip = tmp_path / "Videoclip.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=640x360:d=6", "-f", "lavfi",
         "-i", "sine=frequency=330:duration=6", "-ac", "2", "-shortest", str(clip)],
        check=True,
    )  # fmt: skip
    out = tmp_path / "pkg"

    doc = make_package(
        clip, out, "gl", "Ola mar\n", separator=CopySeparator(), aligner=EvenAligner()
    )

    assert doc.video is not None
    assert doc.video.background == "background.mp4"
    assert doc.cover == "cover.jpg"
    assert validate_package(out) == []


def test_make_keeps_the_cover_art_of_a_song(tmp_path: Path) -> None:
    art = tmp_path / "art.png"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=red:s=300x300",
                    "-frames:v", "1", str(art)], check=True)  # fmt: skip
    song = tmp_path / "Canción.mp3"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=duration=6", "-i", str(art),
         "-map", "0:a", "-map", "1:v", "-c:v", "png", "-disposition:v", "attached_pic", str(song)],
        check=True,
    )  # fmt: skip

    doc = make_package(song, tmp_path / "pkg", "gl", "Ola\n", separator=CopySeparator(),
                       aligner=EvenAligner())  # fmt: skip

    assert doc.video is None
    assert doc.cover == "cover.jpg"


def test_make_without_pictures_has_neither(tmp_path: Path) -> None:
    doc = make_package(_song(tmp_path), tmp_path / "pkg", "gl", "Ola\n", separator=CopySeparator(),
                       aligner=EvenAligner())  # fmt: skip

    assert doc.video is None
    assert doc.cover is None


def test_a_failing_cover_or_background_does_not_lose_the_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clip = tmp_path / "Videoclip.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=320x240:d=6", "-f", "lavfi",
         "-i", "sine=duration=6", "-ac", "2", "-shortest", str(clip)],
        check=True,
    )  # fmt: skip

    def broken(source: Path, out: Path) -> Path:
        raise RuntimeError("ffmpeg failed")

    monkeypatch.setattr("karaoke_engine.make.extract_background", broken)
    monkeypatch.setattr("karaoke_engine.make.extract_cover", broken)
    out = tmp_path / "pkg"

    doc = make_package(clip, out, "gl", "Ola\n", separator=CopySeparator(), aligner=EvenAligner())

    assert doc.video is None
    assert doc.cover is None
    assert validate_package(out) == []


def test_make_joins_galician_pronouns_to_their_verb(tmp_path: Path) -> None:
    doc = make_package(_song(tmp_path), tmp_path / "pkg", "gl", "Collín che o mar\n",
                       separator=CopySeparator(), aligner=EvenAligner())  # fmt: skip

    assert [w.text for w in doc.lines[0].words] == ["Collinche", "o", "mar"]


def test_make_leaves_other_languages_alone(tmp_path: Path) -> None:
    doc = make_package(_song(tmp_path), tmp_path / "pkg", "es", "Dime te quiero\n",
                       separator=CopySeparator(), aligner=EvenAligner())  # fmt: skip

    assert [w.text for w in doc.lines[0].words] == ["Dime", "te", "quiero"]


def test_cli_joins_pronouns_in_a_made_package(tmp_path: Path) -> None:
    out = tmp_path / "pkg"
    make_package(_song(tmp_path), out, "es", "Dixo lle\n", separator=CopySeparator(),
                 aligner=EvenAligner())  # fmt: skip
    doc = load_doc(out / "karaoke.json")
    (out / "karaoke.json").write_text(
        doc.model_copy(update={"language": "gl"}).model_dump_json(), encoding="utf-8"
    )

    assert main(["join-clitics", str(out)]) == 0

    assert [w.text for w in load_doc(out / "karaoke.json").lines[0].words] == ["Díxolle"]
    assert validate_package(out) == []
