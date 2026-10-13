"""Authenticate each MCP HTTP request without buffering streaming responses."""

from fastapi import BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from mcp.server.transport_security import RequestBodyLimitMiddleware
from starlette.datastructures import MutableHeaders
from starlette.requests import Request

from hippobox.core.settings import SETTINGS
from hippobox.platform.core.error import APIKeyException
from hippobox.services.mcp_oauth import issuer
from hippobox.utils.auth import get_current_user


class MCPAuthMiddleware:
    def __init__(self, app):
        self.app = app
        self.limited = RequestBodyLimitMiddleware(app, 16384)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if scope["path"].startswith("/oauth/") or scope["path"].endswith("/connect-mcp"):
            original_send = send

            async def secure_send(message):
                if message["type"] == "http.response.start":
                    headers = MutableHeaders(scope=message)
                    headers["Referrer-Policy"] = "no-referrer"
                    headers["X-Frame-Options"] = "DENY"
                    headers["Content-Security-Policy"] = "frame-ancestors 'none'"
                    headers["Cache-Control"] = "no-store"
                await original_send(message)

            send = secure_send
        if scope["path"].startswith("/oauth/"):
            return await self.limited(scope, receive, send)
        if scope["path"].rstrip("/") != "/mcp" or not SETTINGS.LOGIN_ENABLED:
            return await self.app(scope, receive, send)
        request = Request(scope)
        header = request.headers.get("authorization", "")
        parts = header.split(" ", 1)
        token = (
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=parts[1])
            if len(parts) == 2 and parts[0].lower() == "bearer"
            else None
        )
        background = BackgroundTasks()
        try:
            await get_current_user(background, token, request, request.headers.get("x-api-key"))
        except (HTTPException, APIKeyException):
            challenge = "Bearer"
            if SETTINGS.MCP_OAUTH_ENABLED:
                challenge += f' resource_metadata="{issuer()}/.well-known/oauth-protected-resource/mcp"'
            return await JSONResponse(
                {"error": "invalid_token"}, status_code=401, headers={"WWW-Authenticate": challenge}
            )(scope, receive, send)
        await self.app(scope, receive, send)
        await background()
