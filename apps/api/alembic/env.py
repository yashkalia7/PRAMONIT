"""Alembic environment.

Migrations always run against ``DATABASE_URL_DIRECT`` (Supabase port 5432), never
the pooled endpoint. pgbouncer in transaction mode cannot hold the session state
that DDL and advisory locks require, so running migrations through the pooler
fails in ways that look intermittent and waste an afternoon.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_url() -> tuple[str, dict]:
    raw = settings.DATABASE_URL_DIRECT or settings.DATABASE_URL
    if not raw or "[YOUR-PASSWORD]" in raw:
        # Falls back to the same SQLite file the app uses, so `alembic upgrade
        # head` is runnable before any Supabase credentials exist.
        from app.db.session import SQLITE_DSN

        return SQLITE_DSN, {}
    return settings.migration_db()


def run_migrations_offline() -> None:
    url, _ = _resolve_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        # SQLite cannot ALTER most things in place; batch mode rewrites the
        # table instead, keeping the fallback backend migratable too.
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    url, connect_args = _resolve_url()
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = url

    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
