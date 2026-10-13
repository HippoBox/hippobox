"""Check standalone wheel contents and rebuild the sdist without a frontend checkout."""

import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
dist = root / "src/backend/dist"
wheel = max(dist.glob("hippobox-*.whl"), key=lambda path: path.stat().st_mtime)
with zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()
    for required in [
        "hippobox/server.py",
        "hippobox/cli.py",
        "hippobox/static/dist/index.html",
    ]:
        if required not in names:
            raise SystemExit(f"Package missing {required}")
    if any(".env" == Path(name).name or name.endswith(".db") for name in names):
        raise SystemExit("Package contains local configuration or database")
with tempfile.TemporaryDirectory(prefix="hippobox-package-") as directory:
    folder = Path(directory)
    with tarfile.open(max(dist.glob("hippobox-*.tar.gz"), key=lambda path: path.stat().st_mtime)) as archive:
        archive.extractall(folder, filter="data")
    source = next(folder.glob("hippobox-*"))
    subprocess.run(
        [sys.executable, "-m", "hatchling", "build", "-t", "wheel"],
        cwd=source,
        check=True,
    )
    venv = folder / "installed"
    subprocess.run(["uv", "venv", str(venv), "--python", sys.executable], check=True)
    python = venv / "bin/python"
    subprocess.run(
        ["uv", "pip", "install", "--python", str(python), str(wheel)], check=True
    )
    env = {
        **os.environ,
        "PYTHON_DOTENV_DISABLED": "1",
        "APP_MODE": "development",
        "VDB_ENABLED": "false",
        "DB_NAME": str(folder / "smoke.db"),
        "OBJECT_STORAGE_LOCAL_ROOT": str(folder / "objects"),
        "REDIS_IN_MEMORY": "true",
        "ADMIN_BOOTSTRAP": "false",
    }
    subprocess.run(
        [str(venv / "bin/hippobox"), "--version"], cwd=folder, env=env, check=True
    )
    subprocess.run(
        [
            str(python),
            "-c",
            """from fastapi.testclient import TestClient
from hippobox.server import app
with TestClient(app) as client:
    assert client.get('/ping').status_code == 200
    assert client.get('/app', headers={'Accept': 'text/html'}).status_code == 200
    assert client.get('/api/v1/missing', headers={'Accept': 'text/html'}).status_code == 404
""",
        ],
        cwd=folder,
        env=env,
        check=True,
    )
print("Wheel, CLI, bundled frontend and standalone sdist verified")
