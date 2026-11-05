"""The library: list songs, save corrected lyrics, delete a song."""

from fastapi import APIRouter, Request, Response

from karaoke_contracts import KaraokeDoc
from karaoke_server.access import Owner, Reader
from karaoke_server.errors import ApiError
from karaoke_server.library import InvalidDocError
from karaoke_server.models import SongSummary

router = APIRouter(tags=["songs"])


@router.get("/api/songs")
async def list_songs(request: Request, who: Reader) -> list[SongSummary]:
    return request.app.state.services.library.list()  # type: ignore[no-any-return]


@router.put("/api/songs/{song_id}/doc")
async def save_doc(song_id: str, doc: KaraokeDoc, request: Request, who: Owner) -> KaraokeDoc:
    """Stores corrected lyrics: validated, marked as edited, the original kept beside them."""
    library = request.app.state.services.library
    if library.folder(song_id) is None:
        raise ApiError(404, "not_found", "No such song")
    try:
        return library.save_doc(song_id, doc)  # type: ignore[no-any-return]
    except InvalidDocError as exc:
        issues = [{"path": i.path, "message": i.message} for i in exc.issues]
        raise ApiError(422, "invalid_doc", str(exc), issues=issues) from exc


@router.delete("/api/songs/{song_id}", status_code=204)
async def delete_song(song_id: str, request: Request, who: Owner) -> Response:
    if not request.app.state.services.library.delete(song_id):
        raise ApiError(404, "not_found", "No such song")
    return Response(status_code=204)
