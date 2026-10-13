"""Serve relocatable frontend documents without modifying packaged assets."""

import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from starlette.concurrency import run_in_threadpool
from starlette.responses import FileResponse, Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class RuntimeStaticFiles(StaticFiles):
    """Resolve public paths from trusted application settings, never request headers."""

    def __init__(self, directory: Path, base_path: str, public_url: str) -> None:
        super().__init__(directory=directory, html=True)
        self.base_path = base_path
        self.public_url = public_url.rstrip("/")
        manifest = directory / "deployment-path.json"
        metadata = json.loads(manifest.read_text()) if manifest.exists() else {}
        self.runtime = metadata.get("version") == 2 and metadata.get("mode") == "runtime"
        self.build_origin = str(metadata.get("publicOrigin", "")).rstrip("/")

    def relocate_url(self, value: str) -> str:
        if value.startswith("/") and not value.startswith("//"):
            return self.base_path + value
        if self.build_origin and (
            value == self.build_origin or value.startswith(self.build_origin + "/")
        ):
            return self.public_url + value[len(self.build_origin) :]
        return value

    def render(self, path: Path) -> str:
        source = path.read_text(encoding="utf-8")
        if path.suffix == ".html":
            # Only URL attributes are relocated; prose and embedded application code
            # are never rewritten. Generated documents use quoted attributes.
            source = re.sub(
                r'\b(href|src|content)="([^"]*)"',
                lambda match: (
                    f'{match[1]}="{html.escape(self.relocate_url(html.unescape(match[2])), quote=True)}"'
                ),
                source,
            )
            if "data-b4-app-base" not in source:
                return source  # Static discovery pages keep their document-local anchors.
            source = re.sub(r"<base\b[^>]*data-b4-app-base[^>]*>", "", source)
            source = re.sub(r'<meta\b[^>]*name="b4-base-path"[^>]*>', "", source)
            tags = (
                f'<base data-b4-app-base href="{self.base_path}/">'
                f'<meta name="b4-base-path" content="{self.base_path}">'
            )
            return source.replace("<head>", "<head>" + tags, 1)
        if path.name == "discovery-manifest.json":
            manifest = json.loads(source)
            parsed = urlsplit(self.public_url)
            manifest["origin"] = f"{parsed.scheme}://{parsed.netloc}"
            manifest["pages"] = {
                self.relocate_url(url): digest for url, digest in manifest.get("pages", {}).items()
            }
            return json.dumps(manifest)
        if self.build_origin:
            return source.replace(self.build_origin + "/", self.public_url + "/")
        return source

    async def document_response(self, path: Path, scope: Scope, status_code: int = 200) -> Response:
        if not self.runtime:
            return FileResponse(path, status_code=status_code)
        source = await run_in_threadpool(self.render, path)
        media_type = {
            ".html": "text/html",
            ".xml": "application/xml",
            ".json": "application/json",
            ".txt": "text/plain",
        }[path.suffix]
        response = Response(
            source,
            status_code=status_code,
            media_type=media_type,
            headers={"Cache-Control": "no-store"},
        )
        if scope["method"] == "HEAD":
            response.body = b""
        return response

    async def get_response(self, path: str, scope: Scope) -> Response:
        if not self.runtime:
            return await super().get_response(path, scope)
        # Ignore static validators for runtime documents: their content belongs to
        # this process's configuration, not the immutable file's mtime/ETag.
        clean_scope = dict(scope)
        clean_scope["headers"] = [
            (key, value)
            for key, value in scope["headers"]
            if key.lower() not in {b"if-none-match", b"if-modified-since", b"range", b"if-range"}
        ]
        response = await super().get_response(path, clean_scope)
        if self.runtime and isinstance(response, FileResponse):
            file_path = Path(response.path)
            if file_path.suffix == ".html" or file_path.name in {
                "sitemap.xml",
                "robots.txt",
                "discovery-manifest.json",
            }:
                return await self.document_response(file_path, scope, response.status_code)
            # Retain ordinary conditional/range handling for immutable assets.
            return await super().get_response(path, scope)
        return response
