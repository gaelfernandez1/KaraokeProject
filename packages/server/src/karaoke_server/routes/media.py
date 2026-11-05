"""Files of a song's package, with byte ranges so players can seek."""

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from karaoke_server.access import Reader
from karaoke_server.errors import ApiError
from karaoke_server.library import MEDIA_TYPES

router = APIRouter(tags=["media"])


@router.get("/media/{song_id}/{rel:path}", response_class=Response)
async def media(
    song_id: str, rel: str, request: Request, who: Reader, download: bool = False
) -> Response:
    library = request.app.state.services.library
    if rel == "karaoke.json":
        doc = library.doc(song_id)
        if doc is None:
            raise ApiError(404, "not_found", "No such song")
        # Corrections change it: the browser must ask again every time.
        return JSONResponse(doc.model_dump(mode="json"), headers={"Cache-Control": "no-cache"})
    path = library.media_path(song_id, rel)
    if path is None:
        raise ApiError(404, "not_found", "No such file")
    return FileResponse(
        path,
        media_type=MEDIA_TYPES[path.suffix.lower()],
        headers={"Cache-Control": "no-cache"},
        filename=path.name if download else None,
    )
