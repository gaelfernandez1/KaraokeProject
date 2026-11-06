"""The web app: its built files, and index.html for every route of the single-page app."""

import mimetypes
from pathlib import PurePosixPath

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from karaoke_server.errors import ApiError

router = APIRouter()

mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("font/woff2", ".woff2")

IMMUTABLE = "public, max-age=31536000, immutable"

_NOT_BUILT = """<!doctype html><meta charset="utf-8"><title>Karaoke</title>
<p>The web app is not built yet. Run <code>pnpm --dir web build</code> and reload.</p>"""


@router.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
async def web(path: str, request: Request) -> Response:
    if path == "api" or path.startswith(("api/", "media/")):
        raise ApiError(404, "not_found", "Not found")
    root = request.app.state.services.settings.web_dir
    if root is None or not (root / "index.html").is_file():
        return HTMLResponse(_NOT_BUILT, status_code=503)
    base = root.resolve()
    candidate = (base / path).resolve()
    if path and candidate.is_relative_to(base) and candidate.is_file():
        # Hashed build files never change; everything else is checked on each visit.
        cache = IMMUTABLE if path.startswith("_app/immutable/") else "no-cache"
        return FileResponse(candidate, headers={"Cache-Control": cache})
    # A missing file is missing; anything else is a route of the app.
    if path.startswith("_app/") or "." in PurePosixPath(path).name:
        raise ApiError(404, "not_found", "Not found")
    return FileResponse(base / "index.html", headers={"Cache-Control": "no-cache"})
