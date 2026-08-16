"""Test fixtures.

Every test gets a private SQLite file and a fresh schema. The API is exercised
through a real ASGI transport rather than by calling route functions directly,
so dependency wiring, validation and status codes are all covered.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models import Base
from app.services.storage import reset_store_cache


@pytest.fixture(autouse=True)
def _isolated_media(tmp_path, monkeypatch):
    """Keep every test's uploads inside its own tmp dir."""
    monkeypatch.setattr(settings, "LOCAL_MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    reset_store_cache()
    yield
    reset_store_cache()


@pytest_asyncio.fixture
async def engine(tmp_path):
    db_path = tmp_path / "test.db"
    eng = create_async_engine(
        f"sqlite+aiosqlite:///{db_path.as_posix()}", poolclass=NullPool, future=True
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def session(session_factory) -> AsyncIterator:
    async with session_factory() as s:
        yield s


@pytest_asyncio.fixture
async def client(session_factory) -> AsyncIterator[AsyncClient]:
    async def _override():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = _override
    # ASGITransport does not run the lifespan, which is exactly what we want:
    # no background scheduler firing mid-assertion.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

API = "/api"


def unique_email(prefix: str) -> str:
    # Not a .test/.example domain: RFC 2606 reserves those, and email-validator
    # rejects them, so using one here would fail validation rather than the
    # behaviour under test.
    return f"{prefix}.{uuid.uuid4().hex[:8]}@pramonit.dev"


async def register_coach(client: AsyncClient, **overrides) -> dict:
    payload = {
        "email": unique_email("coach"),
        "password": "coachpass123",
        "full_name": "Rahul Menon",
        "specialization": "Ball mastery",
        "primary_location": "Powai",
        "batches": ["Powai batch"],
        **overrides,
    }
    response = await client.post(f"{API}/auth/register/coach", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    body["password"] = payload["password"]
    body["email"] = payload["email"]
    return body


async def register_student(client: AsyncClient, coach_id: str, **overrides) -> dict:
    payload = {
        "email": unique_email("student"),
        "password": "studentpass123",
        "full_name": "Arjun Mehta",
        "coach_id": coach_id,
        "batch_name": "Powai batch",
        "course": "Ball Mastery — Foundation",
        "dominant_foot": "right",
        "consent_media": True,
        **overrides,
    }
    response = await client.post(f"{API}/auth/register/student", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    body["password"] = payload["password"]
    body["email"] = payload["email"]
    return body


def auth_headers(registration: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {registration['tokens']['access_token']}"}
