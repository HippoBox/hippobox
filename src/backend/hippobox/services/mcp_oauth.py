"""MCP SDK authorization-code/PKCE handlers with durable HippoBox grants."""

import re
import secrets
import time
from urllib.parse import urlparse

from fastapi import HTTPException
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    RefreshToken,
    RegistrationError,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from sqlalchemy import select

from hippobox.core.database import get_db
from hippobox.core.settings import SETTINGS
from hippobox.models import mcp_oauth as store
from hippobox.models.user import Users

SCOPES = ["knowledge:read", "knowledge:write"]
COOKIE = "hippobox_mcp_consent"


def issuer() -> str:
    return (SETTINGS.PUBLIC_API_URL or SETTINGS.APP_BASE_URL).rstrip("/")


def resource() -> str:
    return issuer() + "/mcp"


def allowed_redirect(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        return False
    if parsed.scheme == "https" and parsed.netloc == "chatgpt.com":
        return bool(
            re.fullmatch(r"/connector/oauth/[A-Za-z0-9_-]+", parsed.path)
            or parsed.path == "/connector_platform_oauth_redirect"
        )
    return value in SETTINGS.MCP_OAUTH_REDIRECT_URIS.split()


class HippoOAuthProvider:
    async def get_client(self, client_id):
        value = await store.load(client_id, "client")
        return OAuthClientInformationFull.model_validate(value.data) if value else None

    async def register_client(self, client_info):
        # Public clients use S256 PKCE. No recoverable client secrets are stored.
        if client_info.token_endpoint_auth_method != "none":
            raise RegistrationError("invalid_client_metadata", "Use token_endpoint_auth_method=none with PKCE S256")
        if not client_info.redirect_uris or any(not allowed_redirect(str(uri)) for uri in client_info.redirect_uris):
            raise RegistrationError("invalid_redirect_uri", "Redirect URI is not allowed by this HippoBox server")
        if len(client_info.client_name or "") > 120 or len(client_info.redirect_uris) > 5:
            raise RegistrationError("invalid_client_metadata", "Client metadata is too large")
        await store.save(
            store.record(client_info.client_id, "client", client_info.model_dump(mode="json"), 10 * 365 * 86400)
        )

    async def authorize(self, client, params: AuthorizationParams):
        if not allowed_redirect(str(params.redirect_uri)):
            raise AuthorizeError("invalid_request", "Redirect URI is not allowed")
        if params.resource != resource():
            raise AuthorizeError("invalid_request", "The resource must match this server's MCP URL")
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", params.code_challenge):
            raise AuthorizeError("invalid_request", "A valid S256 PKCE challenge is required")
        if not params.scopes or not set(params.scopes).issubset(SCOPES):
            raise AuthorizeError("invalid_scope", "Select knowledge:read and/or knowledge:write")
        request_id = secrets.token_urlsafe(32)
        await store.save(
            store.record(request_id, "pending", {"client_id": client.client_id, **params.model_dump(mode="json")}, 600)
        )
        base = SETTINGS.FRONTEND_BASE_PATH.rstrip("/")
        return f"{base}/connect-mcp?request={request_id}"

    async def bind_browser(self, request_id, browser_secret):
        async with get_db() as db:
            value = await db.get(store.OAuthRecord, store.digest(request_id))
            value.data = {**value.data, "browser": store.digest(browser_secret)}
            await db.commit()

    async def pending(self, request_id, browser_secret):
        value = await store.load(request_id, "pending")
        if (
            not value
            or value.used
            or not browser_secret
            or not secrets.compare_digest(value.data.get("browser", ""), store.digest(browser_secret))
        ):
            raise HTTPException(400, "Connection request expired. Start again from your MCP client.")
        return value

    async def consent(self, request_id, browser_secret, user_id, approve):
        value = await self.pending(request_id, browser_secret)
        data = value.data
        code = secrets.token_urlsafe(32)
        async with get_db() as db:
            if not await store.consume(db, request_id):
                raise HTTPException(400, "Connection request already used")
            if approve:
                payload = {k: v for k, v in data.items() if k not in {"browser", "state"}}
                payload["subject"] = str(user_id)
                db.add(store.record(code, "code", payload, 120, secrets.token_hex(24)))
            await db.commit()
        return construct_redirect_uri(
            data["redirect_uri"],
            code=code if approve else None,
            error=None if approve else "access_denied",
            state=data.get("state"),
            iss=issuer(),
        )

    async def load_authorization_code(self, client, authorization_code):
        value = await store.load(authorization_code, "code")
        if value:
            return AuthorizationCode(code=authorization_code, expires_at=value.expires, **value.data)

    async def exchange_authorization_code(self, client, authorization_code):
        return await self._exchange(authorization_code.code, "code", client, authorization_code.scopes)

    async def load_refresh_token(self, client, refresh_token):
        value = await store.load(refresh_token, "refresh")
        if value:
            return RefreshToken(token=refresh_token, expires_at=value.expires, **value.data)

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        return await self._exchange(refresh_token.token, "refresh", client, scopes)

    async def _exchange(self, old_token, kind, client, scopes):
        value = await store.load(old_token, kind)
        if not value or value.data["client_id"] != client.client_id or value.data["resource"] != resource():
            raise TokenError("invalid_grant", "Invalid grant")
        user = await Users.get(int(value.data["subject"]))
        if not user or not user.is_active:
            raise TokenError("invalid_grant", "Account unavailable")
        access = "hpm_" + secrets.token_urlsafe(32)
        refresh = "hpr_" + secrets.token_urlsafe(32)
        data = {"client_id": client.client_id, "subject": str(user.id), "resource": resource(), "scopes": scopes}
        async with get_db() as db:
            consumed = await store.consume(db, old_token)
            if not consumed:
                await store.revoke_family(db, value.family)
            else:
                db.add(store.record(access, "access", data, 3600, value.family))
                db.add(store.record(refresh, "refresh", data, 30 * 86400, value.family))
            await db.commit()
        # SDK errors are frozen dataclasses: raise after contextlib has closed the session.
        if not consumed:
            raise TokenError("invalid_grant", "Grant already used; reconnect your MCP client")
        return OAuthToken(
            access_token=access, token_type="Bearer", expires_in=3600, refresh_token=refresh, scope=" ".join(scopes)
        )

    async def load_access_token(self, token):
        value = await store.load(token, "access")
        if not value or value.used or value.data["resource"] != resource():
            return None
        user = await Users.get(int(value.data["subject"]))
        if not user or not user.is_active:
            return None
        return AccessToken(token=token, expires_at=value.expires, **value.data)

    async def revoke_token(self, token):
        value = await store.load(token.token, "access") or await store.load(token.token, "refresh")
        if value:
            async with get_db() as db:
                await store.revoke_family(db, value.family)
                await db.commit()

    async def connections(self, user_id):
        async with get_db() as db:
            values = (
                await db.scalars(
                    select(store.OAuthRecord).where(
                        store.OAuthRecord.kind == "refresh",
                        store.OAuthRecord.used.is_(False),
                        store.OAuthRecord.expires > int(time.time()),
                        store.OAuthRecord.data["subject"].as_string() == str(user_id),
                    )
                )
            ).all()
        result = []
        for value in values:
            client = await self.get_client(value.data["client_id"])
            result.append(
                {
                    "id": value.family,
                    "client_name": client.client_name if client else "MCP client",
                    "scopes": value.data["scopes"],
                }
            )
        return result

    async def disconnect(self, family, user_id):
        if family not in {value["id"] for value in await self.connections(user_id)}:
            raise HTTPException(404, "Connection not found")
        async with get_db() as db:
            await store.revoke_family(db, family)
            await db.commit()


provider = HippoOAuthProvider()
