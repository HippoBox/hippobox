"""Request correlation adapted from the B4 request context boundary.

Pure ASGI preserves streaming MCP responses and avoids buffering their bodies.
"""

import logging
import re
from contextvars import ContextVar
from time import monotonic
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders

request_id: ContextVar[str] = ContextVar("request_id", default="-")
log = logging.getLogger("hippobox.request")


class RequestContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        supplied = Headers(scope=scope).get("x-request-id", "")
        identifier = supplied if re.fullmatch(r"[A-Za-z0-9._-]{1,128}", supplied) else uuid4().hex
        token = request_id.set(identifier)
        started = monotonic()
        status = 500

        async def send_with_context(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = identifier
            await send(message)

        try:
            await self.app(scope, receive, send_with_context)
        finally:
            # Route templates omit query strings, reset tokens and knowledge titles.
            route = scope.get("route")
            path = getattr(route, "path", "<unmatched>")
            log.info(
                "request_id=%s %s %s status=%s duration_ms=%.1f",
                identifier,
                scope["method"],
                path,
                status,
                (monotonic() - started) * 1000,
            )
            request_id.reset(token)
