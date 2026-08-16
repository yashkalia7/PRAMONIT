"""Local-disk media endpoints.

Only mounted when ``STORAGE_BACKEND=local``. These stand in for R2's presigned
PUT and GET so the client's upload code is byte-for-byte the same in development
and production — there is no ``if dev`` branch in the app that production never
exercises.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.services.storage import get_store
from app.services.storage.local_store import LocalDiskStore

router = APIRouter(prefix="/media", tags=["media"])


def _local_store() -> LocalDiskStore:
    store = get_store()
    if not isinstance(store, LocalDiskStore):  # pragma: no cover - config guard
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Local media endpoints are disabled when STORAGE_BACKEND is not 'local'",
        )
    return store


def _check_signature(store: LocalDiskStore, key: str, expires: int, signature: str) -> None:
    if not store.verify(key, expires, signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired media signature"
        )


@router.put("/upload/{key:path}", status_code=status.HTTP_200_OK)
async def upload(
    key: str,
    request: Request,
    expires: int = Query(...),
    signature: str = Query(...),
) -> dict[str, int | str]:
    store = _local_store()
    _check_signature(store, key, expires, signature)

    try:
        path = store.path_for(key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    path.parent.mkdir(parents=True, exist_ok=True)

    # Streamed rather than request.body(): a 200 MB video read whole would pin
    # that much RSS per concurrent upload.
    written = 0
    limit = settings.max_upload_bytes
    with path.open("wb") as handle:
        async for chunk in request.stream():
            written += len(chunk)
            if written > limit:
                handle.close()
                path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Video exceeds the {settings.MAX_UPLOAD_MB} MB limit",
                )
            handle.write(chunk)

    return {"video_key": key, "bytes": written}


@router.get("/file/{key:path}")
async def serve(
    key: str,
    expires: int = Query(...),
    signature: str = Query(...),
) -> Response:
    store = _local_store()
    _check_signature(store, key, expires, signature)

    try:
        path = store.path_for(key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    # FileResponse honours Range requests, which is what lets a coach scrub
    # through a video instead of waiting for the whole file.
    return FileResponse(path, media_type="video/mp4", filename=path.name)
