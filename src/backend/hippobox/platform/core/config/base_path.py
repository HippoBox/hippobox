"""Deployment URL prefix shared by routes, cookies and packaged assets."""

import json
import re
from pathlib import Path

from starlette.types import ASGIApp, Receive, Scope, Send


def normalize_base_path(value: str) -> str:
    if value in ("", "/"):
        return ""
    if not re.fullmatch(r"/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*/?", value):
        raise ValueError(
            "APP_BASE_PATH must be an absolute path of letters, digits, underscores or hyphens"
        )
    return value.rstrip("/")


def validate_frontend_path(dist: Path, base_path: str) -> None:
    if not dist.exists():
        return  # API-only development has no packaged frontend.
    manifest = dist / "deployment-path.json"
    if not manifest.exists() and not base_path:
        return  # Backwards-compatible root builds.
    if not manifest.exists():
        raise ValueError("Packaged frontend lacks deployment-path.json; rebuild with APP_BASE_PATH")
    metadata = json.loads(manifest.read_text())
    if metadata.get("version") == 2 and metadata.get("mode") == "runtime":
        return
    built_path = metadata.get("basePath")
    if built_path != base_path:
        raise ValueError("Frontend build basePath does not match APP_BASE_PATH; rebuild the image")


class PrefixPathMiddleware:
    """Restore a prefix stripped by the reverse proxy for correct absolute redirects.

    ASGI root_path alone does not restore scope.path in a raw Uvicorn deployment.
    All upstream requests must therefore arrive without the public prefix.
    """

    def __init__(self, app: ASGIApp, base_path: str) -> None:
        self.app = app
        self.base_path = base_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.base_path and scope["type"] in {"http", "websocket"}:
            scope = dict(scope)
            scope["path"] = self.base_path + scope["path"]
            if "raw_path" in scope:
                scope["raw_path"] = self.base_path.encode() + scope["raw_path"]
        await self.app(scope, receive, send)
