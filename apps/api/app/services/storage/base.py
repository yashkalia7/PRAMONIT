"""The storage seam.

Video is the one part of this system guaranteed to change: v0 puts raw files on
disk / Cloudflare R2, and if iPhone HEVC footage turns out to be unplayable in a
coach's desktop browser we move to Cloudflare Stream. Every backend implements
this same three-method interface, so that migration touches one file and one env
var — no routes, no models, no UI.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

EXTENSION_BY_MIME = {
    "video/mp4": "mp4",
    "video/quicktime": "mov",
    "video/x-matroska": "mkv",
    "video/webm": "webm",
    "video/3gpp": "3gp",
    "video/x-msvideo": "avi",
    "video/mpeg": "mpeg",
}

ALLOWED_MIME_TYPES = frozenset(EXTENSION_BY_MIME)


@dataclass(slots=True)
class UploadTarget:
    """Everything the client needs to push bytes straight to storage.

    The API never proxies video content — the phone talks directly to R2. That
    keeps the API process small and cheap, and means a 150 MB upload does not
    occupy a worker for two minutes on a bad 4G connection.
    """

    video_key: str
    upload_url: str
    method: str = "PUT"
    headers: dict[str, str] = field(default_factory=dict)
    expires_in: int = 3600


class VideoStore(ABC):
    backend: str = "abstract"

    @abstractmethod
    async def create_upload_target(
        self, *, key: str, content_type: str, content_length: int | None = None
    ) -> UploadTarget: ...

    @abstractmethod
    async def get_playback_url(self, key: str, *, expires_in: int = 3600) -> str: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...


def build_video_key(student_id: uuid.UUID | str, content_type: str, when: datetime) -> str:
    """Date-partitioned key, e.g. ``videos/2026/08/<student>/<uuid>.mp4``.

    Partitioning by month keeps bucket listings usable and makes a future
    "delete everything older than a season" lifecycle rule a prefix match.
    """
    ext = EXTENSION_BY_MIME.get(content_type, "mp4")
    return f"videos/{when:%Y/%m}/{student_id}/{uuid.uuid4().hex}.{ext}"


def guess_extension(content_type: str) -> str:
    return EXTENSION_BY_MIME.get(content_type, "mp4")
