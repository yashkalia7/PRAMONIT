"""S3-compatible video store — Cloudflare R2 in production.

R2 speaks the S3 API, so boto3 works unchanged; only the endpoint URL differs.
R2 charges nothing for egress, which is the reason it is preferred here over
Supabase Storage: a coach reviewing thirty videos a day is pure bandwidth.
"""

from __future__ import annotations

import asyncio
from functools import cached_property
from typing import Any

from app.core.config import settings
from app.services.storage.base import UploadTarget, VideoStore


class S3Store(VideoStore):
    backend = "s3"

    def __init__(
        self,
        *,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        region: str | None = None,
    ) -> None:
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL
        self.access_key = access_key or settings.S3_ACCESS_KEY_ID
        self.secret_key = secret_key or settings.S3_SECRET_ACCESS_KEY
        self.bucket = bucket or settings.S3_BUCKET
        self.region = region or settings.S3_REGION

        missing = [
            name
            for name, value in (
                ("S3_ENDPOINT_URL", self.endpoint_url),
                ("S3_ACCESS_KEY_ID", self.access_key),
                ("S3_SECRET_ACCESS_KEY", self.secret_key),
                ("S3_BUCKET", self.bucket),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "STORAGE_BACKEND=s3 but these are unset: " + ", ".join(missing)
            )

    @cached_property
    def _client(self) -> Any:
        import boto3
        from botocore.config import Config

        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            # SigV4 is mandatory for R2; the default would sign with V2 for some
            # endpoint shapes and every request would 403.
            config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        )

    async def create_upload_target(
        self, *, key: str, content_type: str, content_length: int | None = None
    ) -> UploadTarget:
        params: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": key,
            "ContentType": content_type,
        }

        def _sign() -> str:
            return self._client.generate_presigned_url(
                "put_object", Params=params, ExpiresIn=3600
            )

        url = await asyncio.to_thread(_sign)
        return UploadTarget(
            video_key=key,
            upload_url=url,
            method="PUT",
            # Content-Type is part of the signature, so the client MUST send
            # exactly this value or the PUT is rejected with SignatureDoesNotMatch.
            headers={"Content-Type": content_type},
            expires_in=3600,
        )

    async def get_playback_url(self, key: str, *, expires_in: int = 3600) -> str:
        def _sign() -> str:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )

        return await asyncio.to_thread(_sign)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(
            lambda: self._client.delete_object(Bucket=self.bucket, Key=key)
        )

    async def exists(self, key: str) -> bool:
        def _head() -> bool:
            from botocore.exceptions import ClientError

            try:
                self._client.head_object(Bucket=self.bucket, Key=key)
                return True
            except ClientError:
                return False

        return await asyncio.to_thread(_head)
