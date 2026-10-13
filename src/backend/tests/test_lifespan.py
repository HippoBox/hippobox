import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI

from hippobox import server


def test_missing_embedding_key_fails_before_opening_storage(monkeypatch):
    monkeypatch.setattr(server.SETTINGS, "VDB_ENABLED", True)
    monkeypatch.setattr(server.SETTINGS, "OPENAI_API_KEY", "")
    init_db = AsyncMock()
    qdrant = Mock()
    monkeypatch.setattr(server, "init_db", init_db)
    monkeypatch.setattr(server, "Qdrant", qdrant)

    async def start():
        async with server.lifespan(FastAPI()):
            pytest.fail("Startup must fail when semantic search has no API key")

    with pytest.raises(RuntimeError, match="make backend-dev-local"):
        asyncio.run(start())
    init_db.assert_not_awaited()
    qdrant.assert_not_called()


def test_partial_startup_closes_initialized_resources(monkeypatch):
    monkeypatch.setattr(server.SETTINGS, "VDB_ENABLED", True)
    monkeypatch.setattr(server.SETTINGS, "OPENAI_API_KEY", "test-only-not-a-real-key")
    for name in ("init_db", "ensure_admin_for_login_disabled", "ensure_default_admin_from_settings"):
        monkeypatch.setattr(server, name, AsyncMock())
    monkeypatch.setattr(server.RedisManager, "verify_startup", AsyncMock())
    close_db, close_redis, close_vector = AsyncMock(), AsyncMock(), Mock()
    monkeypatch.setattr(server, "dispose_db", close_db)
    monkeypatch.setattr(server.RedisManager, "close", close_redis)
    monkeypatch.setattr(server, "Qdrant", lambda: SimpleNamespace(client=SimpleNamespace(close=close_vector)))
    monkeypatch.setattr(server, "Embedding", Mock(side_effect=RuntimeError("embedding unavailable")))

    async def start():
        async with server.lifespan(FastAPI()):
            pytest.fail("Startup must fail")

    with pytest.raises(RuntimeError, match="embedding unavailable"):
        asyncio.run(start())
    close_vector.assert_called_once()
    close_db.assert_awaited_once()
    close_redis.assert_awaited_once()


def test_local_mode_starts_without_embedding_key(client):
    response = client.get("/config")
    assert response.status_code == 200
    assert response.json()["vdb_enabled"] is False
    assert client.app.state.QDRANT is None
    assert client.app.state.EMBEDDING is None
