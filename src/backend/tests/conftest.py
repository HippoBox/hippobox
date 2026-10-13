"""Every test uses disposable storage; never read a developer .env."""

import os

os.environ.update(
    {
        "PYTHON_DOTENV_DISABLED": "1",
        "APP_MODE": "development",
        "SECRET_KEY": "HIPPOBOX_DEV_SECRET",
        "VDB_ENABLED": "false",
        "EMAIL_ENABLED": "false",
        "LOGIN_ENABLED": "true",
        "ADMIN_BOOTSTRAP": "false",
        "REDIS_IN_MEMORY": "true",
        "DB_DRIVER": "sqlite+aiosqlite",
        "DB_NAME": ":memory:",
        "SWAGGER_ENABLED": "true",
    }
)

import pytest
from fastapi.testclient import TestClient

from hippobox.core import database
from hippobox.core.settings import SETTINGS
from hippobox.server import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(SETTINGS, "OBJECT_STORAGE_LOCAL_ROOT", tmp_path / "objects")
    monkeypatch.setattr(SETTINGS, "DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(database, "_ENGINE", None)
    monkeypatch.setattr(database, "_SESSION_FACTORY", None)
    with TestClient(create_app()) as client:
        yield client


def account(client, name="alice"):
    # Existing 25-64 character passwords must continue to work.
    form = {"email": f"{name}@example.com", "name": name, "password": "Strong!123" + "a" * 30}
    signup = client.post("/api/v1/auth/signup", json=form)
    assert signup.status_code == 200, signup.text
    login = client.post("/api/v1/auth/login", json={"email": form["email"], "password": form["password"]})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}
