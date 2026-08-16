"""Filesystem-backed video store for development and testing.

Deliberately mimics presigned-URL semantics rather than exposing a plain write
endpoint: the client receives a short-lived, HMAC-signed URL exactly as it would
from R2. The upload flow the frontend implements is therefore the *same* code
path in dev and in production — no ``if (__DEV__)`` branch that only gets
exercised on a developer's laptop.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import time
from pathlib import Path

from app.core.config import settings
from app.services.storage.base import UploadTarget, VideoStore


class LocalDiskStore(VideoStore):
    backend = "local"

    def __init__(self, root: str | Path | None = None, public_base: str | None = None) -> None:
        self.root = Path(root or settings.LOCAL_MEDIA_DIR).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.public_base = (public_base or settings.PUBLIC_BASE_URL).rstrip("/")

    # ---------------------------------------------------------------- signing
    def sign(self, key: str, expires_at: int) -> str:
        payload = f"{key}:{expires_at}".encode()
        digest = hmac.new(settings.JWT_SECRET.encode(), payload, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")

    def verify(self, key: str, expires_at: int, signature: str) -> bool:
        if expires_at < int(time.time()):
            return False
        return hmac.compare_digest(self.sign(key, expires_at), signature)

    # ------------------------------------------------------------- resolution
    def path_for(self, key: str) -> Path:
        """Resolve a key to a path, refusing anything that escapes the root.

        Without this check a key of ``../../.env`` would let a caller write
        outside the media directory.
        """
        candidate = (self.root / key).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError(f"refusing to resolve key outside media root: {key!r}")
        return candidate

    # ---------------------------------------------------------------- VideoStore
    async def create_upload_target(
        self, *, key: str, content_type: str, content_length: int | None = None
    ) -> UploadTarget:
        expires_at = int(time.time()) + 3600
        signature = self.sign(key, expires_at)
        url = (
            f"{self.public_base}{settings.API_PREFIX}/media/upload/{key}"
            f"?expires={expires_at}&signature={signature}"
        )
        return UploadTarget(
            video_key=key,
            upload_url=url,
            method="PUT",
            headers={"Content-Type": content_type},
            expires_in=3600,
        )

    async def get_playback_url(self, key: str, *, expires_in: int = 3600) -> str:
        expires_at = int(time.time()) + expires_in
        signature = self.sign(key, expires_at)
        return (
            f"{self.public_base}{settings.API_PREFIX}/media/file/{key}"
            f"?expires={expires_at}&signature={signature}"
        )

    async def write(self, key: str, data: bytes) -> int:
        def _write() -> int:
            path = self.path_for(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return len(data)

        return await asyncio.to_thread(_write)

    async def read(self, key: str) -> bytes:
        return await asyncio.to_thread(lambda: self.path_for(key).read_bytes())

    async def delete(self, key: str) -> None:
        def _delete() -> None:
            path = self.path_for(key)
            if path.exists():
                path.unlink()

        await asyncio.to_thread(_delete)

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(lambda: self.path_for(key).is_file())
