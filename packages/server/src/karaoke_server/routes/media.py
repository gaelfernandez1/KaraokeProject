"""Files of a song's package, with byte ranges so players can seek."""

import re
from pathlib import PurePosixPath
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from karaoke_server.access import Reader
from karaoke_server.errors import ApiError
from karaoke_server.library import MEDIA_TYPES

router = APIRouter(tags=["media"])

# Characters no file system (or browser) takes in a file name.
_UNSAFE = re.compile(r'[\x00-\x1f\x7f<>:"|?*]+')
NAME_MAX = 120


def download_name(asked: str | None, real: str) -> str:
    """A safe file name for a download: the one asked for, ending as the real file does."""
    suffix = PurePosixPath(real).suffix
    name = re.split(r"[/\\]", asked or "")[-1]
    name = " ".join(_UNSAFE.sub(" ", name).split())
    if not name.lower().endswith(suffix.lower()):
        name += suffix
    stem = name[: len(name) - len(suffix)].strip(" .")[:NAME_MAX].strip(" .")
    return stem + suffix if stem else real


def _disposition(name: str) -> str:
    # As Starlette writes it: plain if it can be, else RFC 5987 (accents, spaces).
    quoted = quote(name)
    if quoted != name:
        return f"attachment; filename*=utf-8''{quoted}"
    return f'attachment; filename="{name}"'


@router.get("/media/{song_id}/{rel:path}", response_class=Response)
# HEAD too: some TV players and download managers ask it before the file.
@router.head("/media/{song_id}/{rel:path}", response_class=Response, include_in_schema=False)
async def media(
    song_id: str,
    rel: str,
    request: Request,
    who: Reader,
    download: bool = False,
    name: str | None = None,
) -> Response:
    """A file of the package; `download` asks the browser to save it, as `name` if given."""
    library = request.app.state.services.library
    headers = {"Cache-Control": "no-cache"}
    if rel == "karaoke.json":
        doc = library.doc(song_id)
        if doc is None:
            raise ApiError(404, "not_found", "No such song")
        if download:
            headers["Content-Disposition"] = _disposition(download_name(name, rel))
        # Corrections change it: the browser must ask again every time.
        return JSONResponse(doc.model_dump(mode="json"), headers=headers)
    path = library.media_path(song_id, rel)
    if path is None:
        raise ApiError(404, "not_found", "No such file")
    if download:
        headers["Content-Disposition"] = _disposition(download_name(name, path.name))
    return FileResponse(path, media_type=MEDIA_TYPES[path.suffix.lower()], headers=headers)
