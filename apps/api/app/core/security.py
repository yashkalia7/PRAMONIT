"""Password hashing and JWT issuing/verification."""

from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import settings
from app.core.timeutil import UTC, now_utc

TokenType = Literal["access", "refresh"]


def _prepare(password: str) -> bytes:
    """Reduce any password to a fixed 44-byte token before bcrypt sees it.

    bcrypt silently truncates input at 72 bytes, so two long passphrases sharing
    a 72-byte prefix would authenticate interchangeably. SHA-256 + base64 first
    means the full password always contributes to the hash.
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(password), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _encode(subject: str, role: str, token_type: TokenType, lifetime: timedelta) -> str:
    issued = now_utc()
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": int(issued.timestamp()),
        "exp": int((issued + lifetime).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, role: str) -> str:
    return _encode(subject, role, "access", timedelta(minutes=settings.ACCESS_TOKEN_MINUTES))


def create_refresh_token(subject: str, role: str) -> str:
    return _encode(subject, role, "refresh", timedelta(days=settings.REFRESH_TOKEN_DAYS))


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decode and validate a JWT. Raises ``jwt.PyJWTError`` on any problem.

    ``expected_type`` guards against a refresh token being replayed as an access
    token — without it, a long-lived refresh token would authorise API calls for
    its entire 30-day life.
    """
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(
            f"expected a {expected_type} token, got {payload.get('type')!r}"
        )
    return payload


def token_expiry_seconds() -> int:
    return settings.ACCESS_TOKEN_MINUTES * 60


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "token_expiry_seconds",
    "UTC",
    "datetime",
]
