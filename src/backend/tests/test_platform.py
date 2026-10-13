import hashlib
import sqlite3
from pathlib import Path

import pytest
from conftest import account
from fastapi.testclient import TestClient

from hippobox.core import database
from hippobox.core.settings import SETTINGS
from hippobox.server import create_app


def test_legacy_upgrade_preserves_account_knowledge_and_key(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as db:
        db.executescript((Path(__file__).parent / "fixtures/legacy-0.1.sql").read_text())
        db.execute(
            "INSERT INTO api_key (user_id,name,access_key,secret_hash,total_requests,is_active,created_at,updated_at) VALUES (1,?,'sk-migration',?,0,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
            ("existing", hashlib.sha256(b"sk-migration-test-only").hexdigest()),
        )
    monkeypatch.setattr(SETTINGS, "DATABASE_URL", f"sqlite+aiosqlite:///{path}")
    monkeypatch.setattr(SETTINGS, "OBJECT_STORAGE_LOCAL_ROOT", tmp_path / "objects")
    monkeypatch.setattr(database, "_ENGINE", None)
    monkeypatch.setattr(database, "_SESSION_FACTORY", None)
    with pytest.raises(RuntimeError, match="PLATFORM_MIGRATE_LEGACY"):
        with TestClient(create_app()):
            pass
    monkeypatch.setattr(SETTINGS, "PLATFORM_MIGRATE_LEGACY", True)
    with TestClient(create_app()) as client:
        login = client.post(
            "/api/v1/auth/login", json={"email": "legacy@example.com", "password": "Strong!123" + "a" * 30}
        )
        assert login.status_code == 200, login.text
        assert login.json()["user"]["id"] == 1
        headers = {"Authorization": "Bearer sk-migration-test-only"}
        notes = client.get("/api/v1/knowledge/list", headers=headers).json()
        assert notes[0]["id"] == 1
        assert notes[0]["title"] == "Before platform"
        assert notes[0]["tags"] == ["retained"]
        assert client.get("/api/v1/auth/me", headers=headers).json()["id"] == 1
    backups = list(tmp_path.glob("*.bak"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as db:
        assert "profile_photo" not in {row[1] for row in db.execute('PRAGMA table_info("user")')}
    monkeypatch.setattr(SETTINGS, "PLATFORM_MIGRATE_LEGACY", False)
    with TestClient(create_app()) as client:
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert len(list(tmp_path.glob("*.bak"))) == 1


def test_platform_profile_keys_and_permissions(client):
    headers = account(client)
    other = account(client, "bob")
    updated = client.patch("/api/v1/auth/me", headers=headers, json={"bio": "My knowledge hub"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["bio"] == "My knowledge hub"
    guide = client.patch("/api/v1/auth/me/guide", headers=headers, json={"seen": True})
    assert guide.status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).json()["guide_seen"] is True
    key = client.post("/api/v1/api-keys", headers=headers, json={"name": "new-key"})
    assert key.status_code == 200, key.text
    key_headers = {"X-API-Key": key.json()["api_key"]}
    assert client.get("/api/v1/knowledge/list", headers=key_headers).status_code == 200
    assert client.get("/api/v1/knowledge/list", headers={**other, **key_headers}).status_code == 401
    assert client.get("/api/v1/auth/admin/users", headers=headers).status_code == 403
    assert client.get("/api/v1/inbox", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/me/password/code", headers=headers).status_code == 403
    assert client.get("/health/ready").json()["status"] == "ok"


def test_deleted_user_identifier_is_not_reused(client):
    from hippobox.models.user import Users

    first = account(client, "first")
    old_id = client.get("/api/v1/auth/me", headers=first).json()["id"]
    client.portal.call(Users.delete, old_id)
    second = account(client, "second")
    new_id = client.get("/api/v1/auth/me", headers=second).json()["id"]
    assert new_id > old_id
    assert client.get("/api/v1/auth/me", headers=first).status_code == 401
