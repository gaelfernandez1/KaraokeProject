"""Downloads the song sets. Audio never goes into git: it lands under bench/data/."""

import csv
import io
import json
import math
import os
import shutil
import tomllib
import urllib.request
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, urlparse

from karaoke_bench import __version__
from karaoke_bench.audio import duration, file_sha256, trim
from karaoke_bench.paths import BenchPaths
from karaoke_bench.reference import Reference, RefLine, RefWord, dump_reference
from karaoke_bench.sets import write_meta

Downloader = Callable[[str, Path], None]

_LANGUAGES = {"English": "en", "Spanish": "es", "French": "fr", "German": "de"}


class FetchError(RuntimeError):
    pass


def http_download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.part")
    request = urllib.request.Request(url, headers={"User-Agent": f"karaoke-bench/{__version__}"})
    with urllib.request.urlopen(request, timeout=60) as response, tmp.open("wb") as out:
        shutil.copyfileobj(response, out)
    os.replace(tmp, dest)


def fetch_jamendo(paths: BenchPaths, download: Downloader = http_download) -> list[str]:
    """Downloads JamendoLyrics audio and builds a reference per song. Safe to re-run."""
    with (paths.sets / "jamendo.toml").open("rb") as handle:
        upstream = tomllib.load(handle)
    timings, lyrics = upstream["jamendolyrics"], upstream["jamalt"]
    work = paths.data / "jamendo" / "_upstream"
    work.mkdir(parents=True, exist_ok=True)

    download(dataset_url(timings, "JamendoLyrics.csv"), work / "JamendoLyrics.csv")
    rows = list(csv.DictReader(io.StringIO((work / "JamendoLyrics.csv").read_text("utf-8"))))
    ids = []
    for row in rows:
        song_id = PurePosixPath(row["Filepath"]).stem
        language = _LANGUAGES[row["Language"]]
        song_dir = paths.data / "jamendo" / song_id
        ids.append(song_id)
        if (song_dir / "reference.json").is_file() and (song_dir / "audio.mp3").is_file():
            continue
        audio = song_dir / "audio.mp3"
        song_dir.mkdir(parents=True, exist_ok=True)
        download(dataset_url(timings, f"subsets/{language}/mp3/{song_id}.mp3"), audio)
        words_txt, words_csv = work / f"{song_id}.words.txt", work / f"{song_id}.csv"
        alignment = work / f"{song_id}.json"
        download(dataset_url(timings, f"lyrics/{song_id}.words.txt"), words_txt)
        download(dataset_url(timings, f"annotations/words/{song_id}.csv"), words_csv)
        download(dataset_url(lyrics, f"alignment/{song_id}.json"), alignment)
        ref = convert_jamendo_song(
            song_id,
            language,
            duration(audio),
            words_txt.read_text("utf-8"),
            words_csv.read_text("utf-8"),
            _load_json(alignment),
        )
        dump_reference(ref, song_dir / "reference.json")
        write_meta(
            song_dir / "meta.toml",
            {
                "title": row["Title"],
                "artist": row["Artist"],
                "language": language,
                "genre": row["Genre"],
                "license": row["LicenseType"],
                "source": row["URL"],
            },
        )
    return ids


def convert_jamendo_song(
    song_id: str,
    language: str,
    duration: float,
    words_txt: str,
    words_csv: str,
    jamalt: dict[str, Any],
) -> Reference:
    """Manual JamendoLyrics word timings under the revised Jam-ALT line texts."""
    texts = [w for w in words_txt.split() if w]
    times = [
        (float(row["word_start"]), float(row["word_end"]))
        for row in csv.DictReader(io.StringIO(words_csv))
    ]
    if len(texts) != len(times):
        raise FetchError(f"{song_id}: {len(texts)} words but {len(times)} timings")
    spans = [
        (float(line["start"]), float(line["end"]), line["text"].strip())
        for line in jamalt["lines"]
        if line["text"].strip()
    ]
    words: list[list[RefWord]] = [[] for _ in spans]
    for text, (start, end) in zip(texts, times, strict=True):
        if spans:
            words[_nearest_line(spans, (start + end) / 2)].append(
                RefWord(text=text, start=start, end=end)
            )
    lines = [
        RefLine(text=text, start=start, end=end, words=line_words)
        for (start, end, text), line_words in zip(spans, words, strict=True)
    ]
    return Reference(
        song_id=song_id,
        language=language,
        duration=duration,
        timing="manual",
        approved=True,
        lines=lines,
    )


def fetch_manifest_set(
    name: str, paths: BenchPaths, download: Downloader = http_download
) -> list[str]:
    """Downloads the audio of a manifest set (e.g. gl) and checks every sha256.

    A `clip = [start, end]` entry keeps only that stretch (a song inside a longer recording),
    saved losslessly as audio.flac next to the checked download.
    """
    with (paths.sets / name / "manifest.toml").open("rb") as handle:
        entries = tomllib.load(handle).get("songs", [])
    ids = []
    for entry in entries:
        suffix = PurePosixPath(urlparse(entry["audio_url"]).path).suffix.lower()
        if not suffix:
            raise FetchError(f"{entry['id']}: audio_url has no file extension")
        song_dir = paths.data / name / entry["id"]
        clip = entry.get("clip")
        source = song_dir / (f"source{suffix}" if clip else f"audio{suffix}")
        ids.append(entry["id"])
        if not (source.is_file() and file_sha256(source) == entry["sha256"]):
            song_dir.mkdir(parents=True, exist_ok=True)
            download(entry["audio_url"], source)
            if file_sha256(source) != entry["sha256"]:
                source.unlink()
                raise FetchError(f"{entry['id']}: sha256 mismatch for {entry['audio_url']}")
        if clip and not (song_dir / "audio.flac").is_file():
            trim(source, float(clip[0]), float(clip[1]), song_dir / "audio.flac")
    return ids


def _nearest_line(spans: list[tuple[float, float, str]], t: float) -> int:
    best, best_gap = 0, math.inf
    for i, (start, end, _) in enumerate(spans):
        gap = 0.0 if start <= t <= end else min(abs(t - start), abs(t - end))
        if gap < best_gap:
            best, best_gap = i, gap
    return best


def dataset_url(source: dict[str, str], path: str) -> str:
    """URL of a file in a Hugging Face dataset at a fixed revision, safe for any file name."""
    base = f"https://huggingface.co/datasets/{source['repo']}/resolve/{source['revision']}"
    return f"{base}/{quote(path)}"


def _load_json(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text("utf-8"))
    return data
