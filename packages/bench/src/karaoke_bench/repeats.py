"""The repeats set: songs whose lyrics write once what is sung several times in a row.

Lyrics sites write a line, a couplet or a stanza sung again right away only once, with a mark
("(x4)" after its last line) or with nothing at all. Doing that to the JamendoLyrics songs that
repeat lines keeps their hand-made timings exact: the audio and the reference stay as they are
and only the lyrics change, in two versions per song (`repeats-marked`, `repeats-unmarked`).
The stanza breaks come from the JamendoLyrics files. The recipe (bench/sets/repeats.toml) is
versioned; the songs are built locally into bench/data/repeats/.
"""

import json
import re
import shutil
import tomllib
from collections.abc import Sequence, Set
from pathlib import Path

from karaoke_bench.paths import BenchPaths
from karaoke_bench.reference import dump_reference, load_reference
from karaoke_bench.sets import read_meta, write_meta

GROUPS = ("repeats-marked", "repeats-unmarked")
# Longest block looked for, and most copies a mark says (lyrics sites write up to "x9").
_LONGEST = 4
_MOST = 9


def collapse_repeats(lines: Sequence[str], breaks: Set[int], marked: bool) -> str:
    """The lyrics with each block of lines sung again right away written once; `marked` adds
    "(xN)" to the block's last line. `breaks` are the lines a blank line follows."""
    keys = [_key(line) for line in lines]
    out: list[str] = []
    i = 0
    while i < len(lines):
        size, count = _repeat_at(keys, i)
        for k in range(size):
            last = k == size - 1
            text = lines[i + k]
            if last and marked and count > 1:
                text = f"{text} (x{count})"
            out.append(text)
            if (i + k + size * (count - 1) if last else i + k) in breaks:
                out.append("")
        i += size * count
    return "\n".join(out).strip("\n")


def build_repeats(paths: BenchPaths, recipe: Path) -> list[str]:
    """Builds both versions of every JamendoLyrics song with repeats into bench/data/repeats/."""
    with recipe.open("rb") as handle:
        data = tomllib.load(handle)
    version = str(data["version"])
    groups = list(data["groups"])
    unknown = [group for group in groups if group not in GROUPS]
    if unknown:
        raise ValueError(f"unknown group '{unknown[0]}' (use {', '.join(GROUPS)})")
    ids = []
    for source in sorted(p.parent for p in (paths.data / "jamendo").glob("*/reference.json")):
        ref = load_reference(source / "reference.json")
        lines = [line.text for line in ref.lines]
        keys = [_key(line) for line in lines]
        if all(_repeat_at(keys, i)[1] == 1 for i in range(len(keys))):
            continue
        breaks = _stanza_breaks(paths, source.name, len(lines))
        meta = read_meta(source / "meta.toml")
        [audio] = sorted(source.glob("audio.*"))
        for group in groups:
            marked = group == "repeats-marked"
            song_id = f"{'marked' if marked else 'unmarked'}-{source.name}"
            ids.append(song_id)
            out_dir = paths.data / "repeats" / song_id
            meta_path = out_dir / "meta.toml"
            if meta_path.is_file() and read_meta(meta_path).get("recipe") == version:
                continue
            out_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(audio, out_dir / audio.name)
            dump_reference(ref.model_copy(update={"song_id": song_id}), out_dir / "reference.json")
            lyrics = collapse_repeats(lines, breaks, marked)
            (out_dir / "lyrics.txt").write_text(lyrics + "\n", encoding="utf-8")
            write_meta(
                meta_path,
                {
                    "title": f"{meta.get('title', source.name)} ({group})",
                    "artist": meta.get("artist"),
                    "language": ref.language,
                    "group": group,
                    "source": source.name,
                    "license": meta.get("license"),
                    "recipe": version,
                },
            )
    # Songs of an older recipe that no longer qualify would stay in the set.
    for stale in sorted((paths.data / "repeats").glob("*")):
        if stale.is_dir() and stale.name not in ids:
            shutil.rmtree(stale)
    return ids


def _key(line: str) -> str:
    """Repeats match without case or punctuation, but an echo in parentheses is not the line it
    echoes: lyrics sites keep backing vocals, they only leave out lines sung again."""
    words = re.sub(r"[^\w]+", " ", line.casefold()).strip()
    return f"({words})" if line.strip().startswith("(") else words


def _repeat_at(keys: Sequence[str], i: int) -> tuple[int, int]:
    """The longest block starting at line i that is sung again right after, and how many times."""
    for size in range(_LONGEST, 0, -1):
        block = keys[i : i + size]
        if len(block) < size or keys[i + size : i + 2 * size] != block:
            continue
        count = 2
        while count < _MOST and keys[i + count * size : i + (count + 1) * size] == block:
            count += 1
        return size, count
    return 1, 1


def _stanza_breaks(paths: BenchPaths, name: str, count: int) -> set[int]:
    """The lines that end a stanza in the JamendoLyrics file (a blank line after them)."""
    upstream = paths.data / "jamendo" / "_upstream" / f"{name}.json"
    if not upstream.is_file():
        return set()
    texts = [line["text"] for line in json.loads(upstream.read_text(encoding="utf-8"))["lines"]]
    if len(texts) != count:
        return set()
    return {i for i, text in enumerate(texts) if text.endswith("\n\n")}
