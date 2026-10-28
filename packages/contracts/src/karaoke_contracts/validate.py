"""Rules a karaoke document must follow beyond what the JSON Schema can express."""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pydantic import ValidationError

from karaoke_contracts.doc import KaraokeDoc, Word, load_doc

# Aligners and float rounding produce sub-millisecond overshoots that nobody can see.
TIME_EPS = 0.001


@dataclass(frozen=True)
class Issue:
    path: str
    message: str


def validate_doc(doc: KaraokeDoc) -> list[Issue]:
    issues: list[Issue] = []
    singer_ids = _unique_ids("singers", [s.id for s in doc.singers], issues)
    _unique_ids("lines", [line.id for line in doc.lines], issues)

    prev_line_start = 0.0
    for i, line in enumerate(doc.lines):
        path = f"lines[{i}]"
        _check_span(path, line.start, line.end, doc.duration, issues)
        if line.start < prev_line_start - TIME_EPS:
            issues.append(Issue(path, "line starts before the previous line"))
        prev_line_start = line.start
        if line.singer is not None and line.singer not in singer_ids:
            issues.append(Issue(f"{path}.singer", f"unknown singer '{line.singer}'"))

        prev_word_start = line.start
        for j, word in enumerate(line.words):
            word_path = f"{path}.words[{j}]"
            _check_span(word_path, word.start, word.end, doc.duration, issues)
            _check_inside(word_path, word.start, word.end, line.start, line.end, "line", issues)
            if word.start < prev_word_start - TIME_EPS:
                issues.append(Issue(word_path, "word starts before the previous word"))
            prev_word_start = word.start
            _check_parts(word_path, word, issues)
    return issues


def validate_file(path: Path) -> list[Issue]:
    """Validates a bare karaoke.json: load errors become issues instead of exceptions."""
    loaded = _load(path)
    return loaded if isinstance(loaded, list) else validate_doc(loaded)


def validate_package(package_dir: Path) -> list[Issue]:
    loaded = _load(package_dir / "karaoke.json")
    if isinstance(loaded, list):
        return loaded
    doc = loaded

    issues = validate_doc(doc)
    refs = {
        "audio.instrumental": doc.audio.instrumental,
        "audio.vocals": doc.audio.vocals,
        "video.background": doc.video.background if doc.video else None,
        "cover": doc.cover,
    }
    for path, ref in refs.items():
        if ref is not None:
            issues.extend(_check_media(package_dir, path, ref))
    return issues


def _unique_ids(collection: str, ids: list[str], issues: list[Issue]) -> set[str]:
    seen: set[str] = set()
    for i, id_ in enumerate(ids):
        if id_ in seen:
            issues.append(Issue(f"{collection}[{i}].id", f"duplicate id '{id_}'"))
        seen.add(id_)
    return seen


def _check_span(path: str, start: float, end: float, duration: float, issues: list[Issue]) -> None:
    if end < start:
        issues.append(Issue(path, f"ends ({end}) before it starts ({start})"))
    if end > duration + TIME_EPS:
        issues.append(Issue(path, f"ends ({end}) after the song ({duration})"))


def _check_inside(
    path: str,
    start: float,
    end: float,
    outer_start: float,
    outer_end: float,
    outer: str,
    issues: list[Issue],
) -> None:
    if start < outer_start - TIME_EPS or end > outer_end + TIME_EPS:
        issues.append(
            Issue(path, f"[{start}, {end}] is outside its {outer} [{outer_start}, {outer_end}]")
        )


def _check_parts(word_path: str, word: Word, issues: list[Issue]) -> None:
    if not word.parts:
        return
    if "".join(p.text for p in word.parts) != word.text:
        issues.append(Issue(f"{word_path}.parts", f"parts do not spell '{word.text}'"))
    prev_start = word.start
    for k, part in enumerate(word.parts):
        part_path = f"{word_path}.parts[{k}]"
        if part.end < part.start:
            issues.append(Issue(part_path, f"ends ({part.end}) before it starts ({part.start})"))
        _check_inside(part_path, part.start, part.end, word.start, word.end, "word", issues)
        if part.start < prev_start - TIME_EPS:
            issues.append(Issue(part_path, "part starts before the previous part"))
        prev_start = part.start


def resolve_media(package_dir: Path, ref: str) -> Path:
    """The real path of a media reference, refusing anything that ends up outside the package.

    Symlinks are resolved first, so a link pointing outside the package is refused too.
    """
    pure = PurePosixPath(ref)
    if pure.is_absolute() or ".." in pure.parts or "\\" in ref:
        raise ValueError(f"'{ref}' must be a relative path inside the package")
    root = package_dir.resolve()
    target = (root / pure).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"'{ref}' points outside the package, but must stay inside the package")
    return target


def _load(path: Path) -> KaraokeDoc | list[Issue]:
    try:
        return load_doc(path)
    except FileNotFoundError:
        return [Issue(path.name, f"{path.name} not found")]
    except OSError as exc:
        return [Issue(path.name, f"cannot read {path.name}: {exc.strerror}")]
    except ValidationError as exc:
        return [
            Issue(".".join(map(str, err["loc"])) or path.name, err["msg"]) for err in exc.errors()
        ]


def _check_media(package_dir: Path, path: str, ref: str) -> list[Issue]:
    try:
        target = resolve_media(package_dir, ref)
    except ValueError as exc:
        return [Issue(path, str(exc))]
    if not target.is_file():
        return [Issue(path, f"file '{ref}' not found in the package")]
    return []
