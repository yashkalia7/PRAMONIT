"""Application configuration.

Everything the app needs is env-driven so that moving from local development to
Supabase + Cloudflare R2 is an .env edit and nothing else.
"""

from __future__ import annotations

import ssl
import uuid
from functools import lru_cache
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=True
    )

    APP_NAME: str = "Pramonit Football Academy"
    ENV: Literal["dev", "prod", "test"] = "dev"
    API_PREFIX: str = "/api"
    APP_TIMEZONE: str = "Asia/Kolkata"

    # --- database -------------------------------------------------------
    # DATABASE_URL         : pooled (:6543) — the running API
    # DATABASE_URL_DIRECT  : direct (:5432) — Alembic migrations
    DATABASE_URL: str = ""
    DATABASE_URL_DIRECT: str = ""

    # --- auth -----------------------------------------------------------
    JWT_SECRET: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 30
    REFRESH_TOKEN_DAYS: int = 30

    # --- club rules -----------------------------------------------------
    WEEKLY_REQUIRED_SUBMISSIONS: int = 2
    AUTO_APPROVE_AFTER_HOURS: int = 72
    SWEEPER_INTERVAL_MINUTES: int = 15
    ENABLE_SWEEPER: bool = True

    # --- storage --------------------------------------------------------
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    LOCAL_MEDIA_DIR: str = "./media"
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    MAX_UPLOAD_MB: int = 200

    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET: str = ""
    S3_REGION: str = "auto"

    CORS_ORIGINS: str = "http://localhost:8081,http://localhost:19006,http://localhost:3000"

    # ------------------------------------------------------------------
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024

    @property
    def db_configured(self) -> bool:
        return bool(self.DATABASE_URL and "[YOUR-PASSWORD]" not in self.DATABASE_URL)

    def runtime_db(self) -> tuple[str, dict[str, Any]]:
        return build_async_dsn(self.DATABASE_URL)

    def migration_db(self) -> tuple[str, dict[str, Any]]:
        return build_async_dsn(self.DATABASE_URL_DIRECT or self.DATABASE_URL)


def build_async_dsn(raw: str) -> tuple[str, dict[str, Any]]:
    """Normalise a libpq URL into a SQLAlchemy+asyncpg URL and connect_args.

    Three things bite people connecting asyncpg to Supabase, and all three are
    handled here:

    1. ``sslmode`` is a libpq keyword that asyncpg does not understand — passing
       it through raises ``TypeError: connect() got an unexpected keyword``.
       We translate it into an ``ssl`` argument instead.
    2. Supabase's pooled endpoint (:6543) is pgbouncer in *transaction* mode,
       which cannot hold server-side prepared statements. asyncpg creates them
       by default, producing intermittent ``DuplicatePreparedStatementError``
       under load. Disabling the statement cache is the documented fix.
    3. pgbouncer already pools, so a second pool in the client is wasteful and
       causes stale connections — NullPool is correct there.
    """
    if not raw:
        return "", {}

    parts = urlsplit(raw)
    scheme = "postgresql+asyncpg"

    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    sslmode = query.pop("sslmode", None)
    # asyncpg understands none of these libpq-isms
    for libpq_only in ("channel_binding", "target_session_attrs", "options", "application_name"):
        query.pop(libpq_only, None)

    connect_args: dict[str, Any] = {}

    if sslmode in (None, "prefer", "require", "allow"):
        # libpq's `require` means "encrypt, but do not verify the certificate".
        # Reproducing that exactly avoids CA-bundle failures on Windows, which
        # has no system trust store that Python reads by default.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx
    elif sslmode in ("verify-ca", "verify-full"):
        connect_args["ssl"] = ssl.create_default_context()
    elif sslmode == "disable":
        pass  # no ssl key at all

    is_pooler = ":6543" in parts.netloc or "pooler.supabase" in parts.netloc
    if is_pooler:
        # Three separate caches have to be defeated to run asyncpg through a
        # transaction-mode pooler (Supabase's Supavisor, or pgbouncer):
        #
        #  1. asyncpg's own statement cache.
        connect_args["statement_cache_size"] = 0
        #  2. asyncpg names its prepared statements __asyncpg_stmt_1__,
        #     __asyncpg_stmt_2__ … per connection. The pooler multiplexes many
        #     client connections onto few server ones, so two clients collide on
        #     the same name and one gets DuplicatePreparedStatementError. Unique
        #     names per statement remove the collision entirely.
        connect_args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid.uuid4()}__"
        #  3. SQLAlchemy's asyncpg dialect keeps its own cache on top, which is
        #     configured through the URL rather than connect_args.
        query["prepared_statement_cache_size"] = "0"

    dsn = urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return dsn, connect_args


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
