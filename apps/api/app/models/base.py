"""Declarative base and shared column helpers."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, TypeVar

from sqlalchemy import DateTime, Enum as SAEnum, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.timeutil import now_utc

E = TypeVar("E", bound=enum.Enum)


class Base(DeclarativeBase):
    """All models inherit from here; Alembic autogenerate reads its metadata."""


def enum_type(py_enum: type[E], name: str) -> SAEnum:
    """VARCHAR-backed enum storing the *value*, not the Python member name."""
    return SAEnum(
        py_enum,
        name=name,
        native_enum=False,
        length=32,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


def pk_uuid(**kwargs: Any) -> Mapped[uuid.UUID]:
    """Client-generated UUID primary key.

    Generating in Python rather than the database keeps the id available before
    flush (handy when building object graphs in the seeder) and avoids depending
    on the pgcrypto/uuid-ossp extensions, which SQLite has no equivalent of.
    """
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4, **kwargs)


def utc_now_column(**kwargs: Any) -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=now_utc, **kwargs)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False
    )
