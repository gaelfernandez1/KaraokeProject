"""The song library: one package folder per song under library/, named by the song's id.

The folders are the truth; the database adds when each song was made. Summaries are kept in
memory and read again when a karaoke.json changes on disk.
"""

import builtins
import re
import shutil
import time
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from pydantic import ValidationError

from karaoke_contracts import (
    Issue,
    KaraokeDoc,
    dump_doc,
    load_doc,
    resolve_media,
    validate_doc,
    validate_package,
)
from karaoke_server.config import Settings
from karaoke_server.db import Database
from karaoke_server.hook import hook_of
from karaoke_server.models import SongSummary

SONG_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
# Trash entries are «<id>-<unix time of deletion>».
_TRASHED_AT = re.compile(r"-(\d{10})$")

# What a package may serve besides karaoke.json (which comes from the parsed document).
MEDIA_TYPES = {
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".mp4": "video/mp4",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

DOC = "karaoke.json"
ORIGINAL = "karaoke.original.json"


class InvalidDocError(ValueError):
    def __init__(self, issues: list[Issue]) -> None:
        super().__init__("; ".join(f"{i.path}: {i.message}" for i in issues[:5]))
        self.issues = issues


def slugify(text: str) -> str:
    """Same rule as `karaoke_engine.make.slug`, kept here so the server stays light."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")[:60].strip("-")


def _copy_package(src: Path, doc: KaraokeDoc, dest: Path) -> None:
    """Copies karaoke.json, the media it names and the licence; nothing else, and never a link.

    A package can come from anyone: a link in it (or any file with a media extension) would be
    copied into the library and served to every phone at home.
    """
    refs = [doc.audio.instrumental, doc.audio.vocals, doc.cover]
    if doc.video is not None:
        refs.append(doc.video.background)
    dest.mkdir(parents=True)
    shutil.copyfile(src / DOC, dest / DOC)
    for ref in filter(None, refs):
        target = dest / ref
        target.parent.mkdir(parents=True, exist_ok=True)
        # resolve_media refuses anything outside the package, links included.
        shutil.copyfile(resolve_media(src, ref), target)
    licence = src / "LICENSE"
    if licence.is_file() and not licence.is_symlink():
        shutil.copyfile(licence, dest / "LICENSE")


def iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class _Cached:
    stamp: tuple[int, int]
    doc: KaraokeDoc
    summary: SongSummary


class Library:
    def __init__(self, settings: Settings, db: Database) -> None:
        self.root = settings.library_dir
        self.trash = settings.trash_dir
        self.db = db
        self._cache: dict[str, _Cached] = {}

    # Reading

    def folder(self, song_id: str) -> Path | None:
        if not SONG_ID.match(song_id):
            return None
        folder = self.root / song_id
        return folder if (folder / DOC).is_file() else None

    def doc(self, song_id: str) -> KaraokeDoc | None:
        cached = self._load(song_id)
        return cached.doc if cached else None

    def summary(self, song_id: str) -> SongSummary | None:
        cached = self._load(song_id)
        return cached.summary if cached else None

    def list(self) -> list[SongSummary]:
        try:
            names = [p.name for p in self.root.iterdir() if p.is_dir()]
        except FileNotFoundError:
            return []
        songs = [s for s in (self.summary(name) for name in names) if s is not None]
        return sorted(songs, key=lambda s: (s.created_at, s.id), reverse=True)

    def media_path(self, song_id: str, rel: str) -> Path | None:
        """A file of the song's package that may be served, or None."""
        folder = self.folder(song_id)
        pure = PurePosixPath(rel)
        if folder is None or not rel or pure.is_absolute() or "\\" in rel:
            return None
        if any(part in ("", ".", "..") or part.startswith(".") for part in pure.parts):
            return None
        if pure.suffix.lower() not in MEDIA_TYPES:
            return None
        root = folder.resolve()
        path = (root / pure).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            return None
        return folder / pure

    # Changing

    def save_doc(self, song_id: str, doc: KaraokeDoc) -> KaraokeDoc:
        """Stores corrected lyrics; the first correction keeps the original beside it."""
        folder = self.folder(song_id)
        if folder is None:
            raise KeyError(song_id)
        saved = doc.model_copy(update={"id": song_id, "edited": True})
        issues = validate_doc(saved) + self._media_issues(folder, saved)
        if issues:
            raise InvalidDocError(issues)
        if not (folder / ORIGINAL).exists():
            shutil.copy2(folder / DOC, folder / ORIGINAL)
        self._write(folder, saved)
        return saved

    def delete(self, song_id: str) -> bool:
        """Moves the song to the trash, where it stays for a while in case it was a mistake."""
        folder = self.folder(song_id)
        if folder is None:
            return False
        self.trash.mkdir(parents=True, exist_ok=True)
        folder.rename(self.trash / f"{song_id}-{int(time.time())}")
        self.db.execute("DELETE FROM songs WHERE id = ?", (song_id,))
        self._cache.pop(song_id, None)
        return True

    def adopt(self, made: Path, title: str, job_id: str | None = None) -> str:
        """Moves a finished package into the library under a free id; returns the id."""
        doc = load_doc(made / DOC)
        song_id = self._free_id(slugify(title) or slugify(doc.title) or "karaoke")
        if doc.id != song_id:
            self._write(made, doc.model_copy(update={"id": song_id}))
        self.root.mkdir(parents=True, exist_ok=True)
        made.rename(self.root / song_id)
        self.db.execute(
            "INSERT OR REPLACE INTO songs (id, created_at, job_id) VALUES (?, ?, ?)",
            (song_id, iso(time.time()), job_id),
        )
        return song_id

    def import_package(self, src: Path) -> str:
        """Copies a package made elsewhere (e.g. by `karaoke make`) into the library."""
        issues = validate_package(src)
        if issues:
            raise InvalidDocError(issues)
        doc = load_doc(src / DOC)
        staging = self.root / f".import-{int(time.time() * 1000)}"
        try:
            _copy_package(src, doc, staging)
            return self.adopt(staging, doc.title)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    def purge_trash(self, days: float = 30) -> int:
        limit = time.time() - days * 86400
        purged = 0
        for entry in self.trash.glob("*"):
            # When it was deleted is in its name: the folder's own time is when it was made.
            stamp = _TRASHED_AT.search(entry.name)
            deleted = int(stamp.group(1)) if stamp else entry.stat().st_mtime
            if deleted < limit:
                shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
                purged += 1
        return purged

    # Inside

    def _load(self, song_id: str) -> _Cached | None:
        folder = self.folder(song_id)
        if folder is None:
            self._cache.pop(song_id, None)
            return None
        stat = (folder / DOC).stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
        cached = self._cache.get(song_id)
        if cached and cached.stamp == stamp:
            return cached
        try:
            doc = load_doc(folder / DOC)
        except (ValidationError, ValueError, OSError):
            return None
        summary = SongSummary(
            id=song_id,
            title=doc.title,
            artist=doc.artist,
            language=doc.language,
            duration=doc.duration,
            cover=doc.cover,
            has_video=bool(doc.video and doc.video.background),
            created_at=self._created_at(song_id, stat.st_mtime),
            edited=doc.edited,
            lyrics_source=doc.provenance.lyrics_source,
            hook=hook_of(doc),
        )
        self._cache[song_id] = _Cached(stamp, doc, summary)
        return self._cache[song_id]

    def _created_at(self, song_id: str, fallback: float) -> str:
        rows = self.db.query("SELECT created_at FROM songs WHERE id = ?", (song_id,))
        if rows:
            return str(rows[0]["created_at"])
        created = iso(fallback)
        self.db.execute(
            "INSERT OR IGNORE INTO songs (id, created_at) VALUES (?, ?)", (song_id, created)
        )
        return created

    def _free_id(self, base: str) -> str:
        song_id, n = base, 2
        while (self.root / song_id).exists():
            song_id = f"{base}-{n}"
            n += 1
        return song_id

    @staticmethod
    def _media_issues(folder: Path, doc: KaraokeDoc) -> builtins.list[Issue]:
        refs = {
            "audio.instrumental": doc.audio.instrumental,
            "audio.vocals": doc.audio.vocals,
            "video.background": doc.video.background if doc.video else None,
            "cover": doc.cover,
        }
        issues: builtins.list[Issue] = []
        for path, ref in refs.items():
            if ref is None:
                continue
            try:
                found = resolve_media(folder, ref).is_file()
            except ValueError as exc:
                issues.append(Issue(path, str(exc)))
                continue
            if not found:
                issues.append(Issue(path, f"file '{ref}' not found in the package"))
        return issues

    def _write(self, folder: Path, doc: KaraokeDoc) -> None:
        staged = folder / ".karaoke.json.tmp"
        dump_doc(doc, staged)
        staged.replace(folder / DOC)
