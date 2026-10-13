"""OAuth discovery, MCP SDK protocol endpoints, and authenticated user consent."""

import re
import secrets
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from mcp.server.auth.handlers.authorize import AuthorizationHandler
from mcp.server.auth.handlers.register import RegistrationHandler
from mcp.server.auth.handlers.token import TokenHandler
from mcp.server.auth.middleware.client_auth import ClientAuthenticator
from mcp.server.auth.provider import construct_redirect_uri
from mcp.server.auth.settings import ClientRegistrationOptions
from pydantic import BaseModel, Field

from hippobox.core.redis import RedisManager
from hippobox.core.settings import SETTINGS
from hippobox.models.mcp_oauth import digest
from hippobox.services.mcp_oauth import COOKIE, SCOPES, issuer, provider, resource
from hippobox.utils.auth import get_current_user


def enabled():
    if not SETTINGS.MCP_OAUTH_ENABLED:
        raise HTTPException(404, "MCP OAuth is disabled")


router = APIRouter(dependencies=[Depends(enabled)], include_in_schema=False)


async def rate_limit(request: Request, name: str, limit: int = 60):
    cache = await RedisManager.get_client()
    key = f"mcp-oauth:{name}:{digest(request.client.host if request.client else 'unknown')}"
    count = await cache.incr(key)
    if count == 1:
        await cache.expire(key, 60)
    if count > limit:
        raise HTTPException(429, "Please try again in a minute", headers={"Retry-After": "60"})


def response(data, status=200):
    return JSONResponse(data, status_code=status, headers={"Cache-Control": "no-store", "Pragma": "no-cache"})


@router.get("/.well-known/oauth-authorization-server")
async def metadata():
    return {
        "issuer": issuer(),
        "authorization_endpoint": issuer() + "/oauth/authorize",
        "token_endpoint": issuer() + "/oauth/token",
        "registration_endpoint": issuer() + "/oauth/register",
        "revocation_endpoint": issuer() + "/oauth/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["none"],
        "revocation_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": SCOPES,
        "authorization_response_iss_parameter_supported": True,
    }


@router.get("/.well-known/oauth-protected-resource")
@router.get("/.well-known/oauth-protected-resource/mcp")
async def protected_resource():
    return {
        "resource": resource(),
        "authorization_servers": [issuer()],
        "scopes_supported": SCOPES,
        "bearer_methods_supported": ["header"],
        "resource_name": "HippoBox",
    }


@router.post("/oauth/register")
async def register(request: Request):
    await rate_limit(request, "register", 10)
    try:
        return await RegistrationHandler(
            provider, ClientRegistrationOptions(enabled=True, valid_scopes=SCOPES, default_scopes=SCOPES)
        ).handle(request)
    except ValueError:
        return response({"error": "invalid_client_metadata"}, 400)


@router.get("/oauth/authorize")
async def authorize(request: Request):
    await rate_limit(request, "authorize")
    result = await AuthorizationHandler(provider).handle(request)
    location = result.headers.get("location", "")
    if location.startswith((SETTINGS.FRONTEND_BASE_PATH.rstrip("/") or "") + "/connect-mcp?"):
        request_id = parse_qs(urlparse(location).query)["request"][0]
        secret = secrets.token_urlsafe(32)
        await provider.bind_browser(request_id, secret)
        result.set_cookie(
            COOKIE, secret, max_age=600, httponly=True, secure=issuer().startswith("https:"), samesite="lax"
        )
    elif location:
        result.headers["location"] = construct_redirect_uri(location, iss=issuer())
    result.headers["Referrer-Policy"] = "no-referrer"
    return result


@router.post("/oauth/token")
async def token(request: Request):
    await rate_limit(request, "token", 120)
    form = await request.form()
    if form.get("resource") != resource():
        return response({"error": "invalid_target", "error_description": "MCP resource does not match"}, 400)
    if form.get("grant_type") == "authorization_code" and not re.fullmatch(
        r"[A-Za-z0-9._~-]{43,128}", str(form.get("code_verifier", ""))
    ):
        return response({"error": "invalid_grant", "error_description": "Invalid PKCE verifier"}, 400)
    return await TokenHandler(provider, ClientAuthenticator(provider)).handle(request)


@router.post("/oauth/revoke")
async def revoke(request: Request):
    await rate_limit(request, "revoke")
    form = await request.form()
    client = await provider.get_client(str(form.get("client_id", "")))
    if not client:
        return response({"error": "invalid_client"}, 401)
    raw = str(form.get("token", ""))
    value = await provider.load_refresh_token(client, raw) or await provider.load_access_token(raw)
    if value and value.client_id == client.client_id:
        await provider.revoke_token(value)
    return response({})


@router.get("/oauth/consent")
async def consent_info(request: Request, request_id: str):
    value = await provider.pending(request_id, request.cookies.get(COOKIE))
    client = await provider.get_client(value.data["client_id"])
    return response(
        {
            "client_name": client.client_name or "MCP client",
            "scopes": value.data["scopes"],
            "redirect_uri": value.data["redirect_uri"],
        }
    )


class Consent(BaseModel):
    request_id: str = Field(min_length=43, max_length=43)
    approve: bool


@router.get("/oauth/connections")
async def connections(user=Depends(get_current_user)):
    return response(await provider.connections(user.id))


@router.delete("/oauth/connections/{connection_id}")
async def disconnect(connection_id: str, user=Depends(get_current_user)):
    await provider.disconnect(connection_id, user.id)
    return response({"status": "revoked"})


@router.post("/oauth/consent")
async def consent(request: Request, form: Consent, user=Depends(get_current_user)):
    origin = request.headers.get("origin")
    if origin not in {issuer(), (SETTINGS.PUBLIC_APP_URL or SETTINGS.APP_BASE_URL).rstrip("/")}:
        raise HTTPException(403, "Invalid consent origin")
    location = await provider.consent(form.request_id, request.cookies.get(COOKIE), user.id, form.approve)
    result = response({"redirect_uri": location})
    result.delete_cookie(COOKIE)
    return result
