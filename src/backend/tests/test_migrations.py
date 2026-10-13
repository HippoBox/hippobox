"""Exercise the existing PostgreSQL-only Alembic history in an isolated container."""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import asyncpg
import pytest


@pytest.mark.skipif(os.getenv("HIPPOBOX_TEST_POSTGRES") != "1", reason="Run make test-migrations-postgres")
def test_legacy_database_upgrade_preserves_ids_and_keys():
    root = Path(__file__).resolve().parents[1]
    container = subprocess.check_output(
        [
            "docker",
            "run",
            "--rm",
            "-d",
            "-e",
            "POSTGRES_PASSWORD=hippobox-test-only",
            "-p",
            "127.0.0.1::5432",
            "postgres:15-alpine",
        ],
        text=True,
    ).strip()
    try:
        info = json.loads(subprocess.check_output(["docker", "inspect", container], text=True))[0]
        port = info["NetworkSettings"]["Ports"]["5432/tcp"][0]["HostPort"]
        env = {
            **os.environ,
            "DB_NAME": "postgres",
            "DB_DRIVER": "postgresql+asyncpg",
            "DB_HOST": "127.0.0.1",
            "DB_PORT": port,
            "DB_USER": "postgres",
            "DB_PASSWORD": "hippobox-test-only",
        }
        for _ in range(60):
            if (
                subprocess.run(
                    ["docker", "exec", container, "pg_isready", "-U", "postgres"], capture_output=True
                ).returncode
                == 0
            ):
                break
            time.sleep(0.5)
        else:
            pytest.fail("Disposable PostgreSQL did not become ready")

        def upgrade(revision):
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", revision],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, result.stderr

        async def data(verify=False):
            db = await asyncpg.connect(host="127.0.0.1", port=int(port), user="postgres", password="hippobox-test-only")
            try:
                if verify:
                    assert tuple(await db.fetchrow("SELECT id, user_id, title, content FROM knowledge")) == (
                        99,
                        42,
                        "Legacy note",
                        "Original content",
                    )
                    assert tuple(await db.fetchrow("SELECT id, user_id, secret_hash FROM api_key")) == (
                        7,
                        42,
                        "unchanged-sha256",
                    )
                    assert await db.fetchval('SELECT id FROM "user"') == 42
                    assert await db.fetchval("SELECT count(*) FROM knowledge_tag") == 1
                    assert (
                        await db.fetchval("SELECT name FROM topic WHERE id=(SELECT topic_id FROM knowledge)")
                        == "Engineering"
                    )
                    return
                await db.execute("""INSERT INTO "user" VALUES (42, 'legacy@example.com', 'legacy', 'USER', true, true, now(), now());
                    INSERT INTO knowledge VALUES (99, 42, 'Engineering', '["api"]', 'Legacy note', 'Original content', now(), now());
                    INSERT INTO api_key VALUES (7, 42, 'legacy', 'sk-prefix', 'unchanged-sha256', 0, true, NULL, now(), now());""")
            finally:
                await db.close()

        upgrade("18071a646038")
        asyncio.run(data())
        upgrade("head")
        asyncio.run(data(verify=True))
        # Run the platform bridge against the actual legacy PostgreSQL schema.
        migrated = subprocess.run(
            [
                sys.executable,
                "-c",
                """
from fastapi.testclient import TestClient
from hippobox.server import app
with TestClient(app) as client:
    assert client.get('/health/ready').status_code == 200
    response = client.post('/api/v1/auth/signup', json={
        'name': 'after-migration', 'email': 'after@example.com', 'password': 'Strong!123456789'})
    assert response.status_code == 200, response.text
""",
            ],
            cwd=root,
            env={**env, "PLATFORM_MIGRATE_LEGACY": "true", "VDB_ENABLED": "false", "REDIS_IN_MEMORY": "true"},
            capture_output=True,
            text=True,
        )
        assert migrated.returncode == 0, migrated.stderr

    finally:
        subprocess.run(["docker", "rm", "-f", container], capture_output=True, check=True)
