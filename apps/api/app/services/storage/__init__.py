"""Video storage factory."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.services.storage.base import (
    ALLOWED_MIME_TYPES,
    EXTENSION_BY_MIME,
    UploadTarget,
    VideoStore,
    build_video_key,
    guess_extension,
)
from app.services.storage.local_store import LocalDiskStore
from app.services.storage.s3_store import S3Store


@lru_cache
def get_store() -> VideoStore:
    if settings.STORAGE_BACKEND == "s3":
        return S3Store()
    return LocalDiskStore()


def reset_store_cache() -> None:
    """Used by tests that flip STORAGE_BACKEND at runtime."""
    get_store.cache_clear()


__all__ = [
    "VideoStore",
    "UploadTarget",
    "LocalDiskStore",
    "S3Store",
    "get_store",
    "reset_store_cache",
    "build_video_key",
    "guess_extension",
    "ALLOWED_MIME_TYPES",
    "EXTENSION_BY_MIME",
]
