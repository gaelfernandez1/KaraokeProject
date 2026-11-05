"""New songs coming in: multipart uploads written straight to the job's folder, then checked.

Nothing goes through /tmp, which is in RAM here, and a body larger than the limit is refused
from its Content-Length before a byte is read.
"""

import asyncio
import contextlib
import json
import re
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePath
from urllib.parse import parse_qsl

from python_multipart import FormParser
from python_multipart.multipart import Field, File, parse_options_header

MIB = 1024 * 1024
MAX_FIELD = 64 * 1024
# A multipart body carries some bytes of its own: part headers and the text fields.
OVERHEAD = 256 * 1024


class IntakeError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


@dataclass(frozen=True)
class Form:
    fields: dict[str, str]
    file: Path | None
    filename: str | None


def _extension(filename: str | None) -> str:
    suffix = PurePath(filename or "").suffix.lower()
    return suffix if re.fullmatch(r"\.[a-z0-9]{1,5}", suffix) else ""


async def receive_form(
    headers: Mapping[str, str], chunks: AsyncIterator[bytes], dest: Path, max_bytes: int
) -> Form:
    content_type, params = parse_options_header(headers.get("content-type", ""))
    length = headers.get("content-length")
    if length is None or not length.isdigit():
        raise IntakeError(411, "bad_form", "The upload must say its length")
    if content_type == b"application/x-www-form-urlencoded":
        # A link and text fields only (handy from scripts and curl).
        if int(length) > OVERHEAD:
            raise IntakeError(413, "bad_form", "The form is too long")
        body = b"".join([chunk async for chunk in chunks])
        pairs = parse_qsl(body.decode("utf-8", "replace"), keep_blank_values=True)
        return Form(dict(pairs), None, None)
    if content_type != b"multipart/form-data" or not params.get(b"boundary"):
        raise IntakeError(422, "bad_form", "Send the song as multipart/form-data")
    if int(length) > max_bytes + OVERHEAD:
        limit = max_bytes // (1024**3) or max_bytes // MIB
        unit = "GB" if max_bytes >= 1024**3 else "MB"
        raise IntakeError(413, "too_big", f"Files can be up to {limit} {unit}")

    fields: dict[str, str] = {}
    files: list[File] = []

    def on_field(field: Field) -> None:
        if field.field_name and field.value is not None:
            if len(field.value) > MAX_FIELD:
                raise IntakeError(422, "bad_form", "A text field is too long")
            fields[field.field_name.decode()] = field.value.decode("utf-8", "replace")

    def on_file(file: File) -> None:
        files.append(file)

    dest.mkdir(parents=True, exist_ok=True)
    config = {
        "UPLOAD_DIR": str(dest),
        "MAX_MEMORY_FILE_SIZE": 0,
        "UPLOAD_DELETE_TMP": False,
        "MAX_BODY_SIZE": max_bytes + OVERHEAD,
    }
    parser = FormParser(
        content_type.decode(), on_field, on_file, boundary=params[b"boundary"], config=config
    )
    try:
        async for chunk in chunks:
            parser.write(chunk)
        parser.finalize()
    except BaseException:
        for file in files:
            _discard(file)
        for leftover in dest.iterdir():
            leftover.unlink(missing_ok=True)
        raise

    upload = next((f for f in files if f.field_name == b"file"), None)
    for other in files:
        if other is not upload:
            _discard(other)
    if upload is None or not upload.size:
        if upload:
            _discard(upload)
        return Form(fields, None, None)
    upload.file_object.close()
    filename = (upload.file_name or b"").decode("utf-8", "replace") or None
    temp = Path(
        upload.actual_file_name.decode()
        if isinstance(upload.actual_file_name, bytes)
        else str(upload.actual_file_name)
    )
    final = dest / f"source{_extension(filename)}"
    temp.replace(final)
    return Form(fields, final, filename)


def _discard(file: File) -> None:
    with contextlib.suppress(Exception):
        file.file_object.close()
    name = file.actual_file_name
    if name:
        Path(name.decode() if isinstance(name, bytes) else str(name)).unlink(missing_ok=True)


@dataclass(frozen=True)
class MediaInfo:
    duration: float
    has_audio: bool
    title: str | None
    artist: str | None


async def media_info(path: Path) -> MediaInfo:
    """What ffprobe says about a file: its length, whether it has sound, its title and artist."""
    process = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:format_tags=title,artist:stream=codec_type:stream_tags=title,artist",
        "-of",
        "json",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        out, _ = await asyncio.wait_for(process.communicate(), timeout=60)
    except TimeoutError:
        process.kill()
        return MediaInfo(0.0, False, None, None)
    try:
        data = json.loads(out or b"{}")
    except ValueError:
        data = {}
    streams = data.get("streams") or []
    fmt = data.get("format") or {}
    tags = {k.lower(): v for k, v in (fmt.get("tags") or {}).items()}
    for stream in streams:
        for key, value in (stream.get("tags") or {}).items():
            tags.setdefault(key.lower(), value)
    try:
        duration = float(fmt.get("duration") or 0)
    except ValueError:
        duration = 0.0
    has_audio = process.returncode == 0 and any(s.get("codec_type") == "audio" for s in streams)
    return MediaInfo(
        duration,
        has_audio,
        (tags.get("title") or "").strip() or None,
        (tags.get("artist") or "").strip() or None,
    )
