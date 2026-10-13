"""Run the built UI against a disposable backend for browser verification."""

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src/backend"))
with TemporaryDirectory(prefix="hippobox-browser-") as directory:
    os.environ.update(
        {
            "PYTHON_DOTENV_DISABLED": "1",
            "APP_MODE": "development",
            "LOGIN_ENABLED": "true",
            "EMAIL_ENABLED": "false",
            "VDB_ENABLED": "false",
            "ADMIN_BOOTSTRAP": "false",
            "REDIS_IN_MEMORY": "true",
            "DB_DRIVER": "sqlite+aiosqlite",
            "DB_NAME": str(Path(directory) / "test.db"),
            "OBJECT_STORAGE_LOCAL_ROOT": str(Path(directory) / "objects"),
            "FRONTEND_BASE_PATH": "",
            "MCP_OAUTH_ENABLED": "true",
            "PUBLIC_API_URL": "http://127.0.0.1:8127",
            "PUBLIC_APP_URL": "http://127.0.0.1:8127",
        }
    )
    uvicorn.run("hippobox.server:app", host="127.0.0.1", port=8127, log_level="warning")
