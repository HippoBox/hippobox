import base64
import hashlib
import json
import time
from urllib.parse import parse_qs, urlparse

import pytest
from conftest import account

from hippobox.core.settings import SETTINGS
from hippobox.services.mcp_oauth import provider

ORIGIN = "http://localhost:8000"
RESOURCE = ORIGIN + "/mcp"
CALLBACK = "https://chatgpt.com/connector_platform_oauth_redirect"
VERIFIER = "a" * 64
CHALLENGE = base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).decode().rstrip("=")


@pytest.fixture(autouse=True)
def enable_oauth(monkeypatch):
    monkeypatch.setattr(SETTINGS, "MCP_OAUTH_ENABLED", True)
    monkeypatch.setattr(SETTINGS, "PUBLIC_API_URL", ORIGIN)


def register(client, **overrides):
    result = client.post(
        "/oauth/register",
        json={
            "redirect_uris": [CALLBACK],
            "client_name": "ChatGPT test",
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            **overrides,
        },
    )
    assert result.status_code == 201, result.text
    return result.json()["client_id"]


def authorize(client, client_id, **overrides):
    return client.get(
        "/oauth/authorize",
        params={
            "client_id": client_id,
            "redirect_uri": CALLBACK,
            "response_type": "code",
            "scope": "knowledge:read knowledge:write",
            "code_challenge": CHALLENGE,
            "code_challenge_method": "S256",
            "resource": RESOURCE,
            "state": "preserve-this",
            **overrides,
        },
        follow_redirects=False,
    )


def consent(client, client_id, headers, approve=True, **overrides):
    result = authorize(client, client_id, **overrides)
    assert result.status_code == 302, result.text
    request_id = parse_qs(urlparse(result.headers["location"]).query)["request"][0]
    info = client.get("/oauth/consent", params={"request_id": request_id})
    assert info.status_code == 200, info.text
    assert info.json()["client_name"] == "ChatGPT test"
    result = client.post(
        "/oauth/consent", headers={**headers, "Origin": ORIGIN}, json={"request_id": request_id, "approve": approve}
    )
    assert result.status_code == 200, result.text
    parsed = parse_qs(urlparse(result.json()["redirect_uri"]).query)
    assert parsed["state"] == ["preserve-this"]
    assert parsed["iss"] == [ORIGIN]
    return parsed.get("code", [None])[0]


def exchange(client, client_id, code, **overrides):
    return client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "redirect_uri": CALLBACK,
            "code_verifier": VERIFIER,
            "resource": RESOURCE,
            **overrides,
        },
    )


def test_discovery_and_mcp_challenge(client):
    result = client.post("/mcp", json={})
    assert result.status_code == 401
    assert client.post("/mcp", json={}, headers={"X-API-Key": "invalid"}).status_code == 401
    assert (
        'resource_metadata="http://localhost:8000/.well-known/oauth-protected-resource/mcp"'
        in result.headers["www-authenticate"]
    )
    meta = client.get("/.well-known/oauth-authorization-server").json()
    assert meta["code_challenge_methods_supported"] == ["S256"]
    assert meta["token_endpoint_auth_methods_supported"] == ["none"]
    assert client.get("/.well-known/oauth-protected-resource/mcp").json()["resource"] == RESOURCE
    assert client.get("/.well-known/missing", headers={"Accept": "text/html"}).status_code == 404


def test_oauth_end_to_end_and_restart(client):
    from hippobox.core.database import dispose_db, init_db

    user = account(client)
    other = account(client, "bob")
    client.post("/api/v1/knowledge/", headers=other, json={"title": "Private Bob", "content": "Hidden"})
    client_id = register(client)
    code = consent(client, client_id, user)
    result = exchange(client, client_id, code)
    assert result.status_code == 200, result.text
    tokens = result.json()
    headers = {"Authorization": "Bearer " + tokens["access_token"], "Accept": "application/json, text/event-stream"}
    initialized = client.post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "oauth-test", "version": "1"},
            },
        },
    )
    assert initialized.status_code == 200, initialized.text
    headers["mcp-session-id"] = initialized.headers["mcp-session-id"]
    result = client.post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "create_knowledge", "arguments": {"title": "OAuth note", "content": "Saved"}},
        },
    )
    assert result.status_code == 200, result.text
    message = (
        result.json()
        if "application/json" in result.headers["content-type"]
        else next(json.loads(line[6:]) for line in result.text.splitlines() if line.startswith("data: "))
    )
    assert not message["result"].get("isError"), result.text
    notes = client.get("/api/v1/knowledge/list", headers=headers).json()
    assert [note["title"] for note in notes] == ["OAuth note"]
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 403
    assert client.post("/api/v1/api_key", headers=headers, json={"name": "escalate"}).status_code == 403
    client.portal.call(dispose_db)
    client.portal.call(init_db)
    assert client.get("/api/v1/knowledge/list", headers=headers).status_code == 200
    assert client.portal.call(provider.get_client, client_id)
    renewed = client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": tokens["refresh_token"],
            "resource": RESOURCE,
        },
    )
    assert renewed.status_code == 200, renewed.text
    assert renewed.json()["refresh_token"] != tokens["refresh_token"]
    replay = client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": tokens["refresh_token"],
            "resource": RESOURCE,
        },
    )
    assert replay.status_code == 400
    assert client.portal.call(provider.load_access_token, renewed.json()["access_token"]) is None


def test_pkce_resource_client_binding_and_replay(client):
    user = account(client)
    client_id = register(client)
    code = consent(client, client_id, user)
    assert exchange(client, client_id, code, code_verifier="b" * 64).status_code == 400
    assert exchange(client, client_id, code, resource="https://attacker.test/mcp").status_code == 400
    assert exchange(client, register(client), code).status_code == 400
    assert exchange(client, client_id, code, redirect_uri="https://attacker.test").status_code == 400
    valid = exchange(client, client_id, code)
    assert valid.status_code == 200
    assert exchange(client, client_id, code).status_code == 400
    assert client.portal.call(provider.load_access_token, valid.json()["access_token"]) is None


def test_read_scope_and_revocation(client):
    user = account(client)
    client_id = register(client)
    code = consent(client, client_id, user, scope="knowledge:read")
    tokens = exchange(client, client_id, code).json()
    headers = {"Authorization": "Bearer " + tokens["access_token"]}
    assert client.get("/api/v1/knowledge/list", headers=headers).status_code == 200
    assert (
        client.post("/api/v1/knowledge/", headers=headers, json={"title": "Denied", "content": "No"}).status_code == 403
    )
    wider = client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": tokens["refresh_token"],
            "resource": RESOURCE,
            "scope": "knowledge:write",
        },
    )
    assert wider.status_code == 400
    assert (
        client.post("/oauth/revoke", data={"client_id": client_id, "token": tokens["refresh_token"]}).status_code == 200
    )
    assert client.get("/api/v1/knowledge/list", headers=headers).status_code == 401


def test_untrusted_callbacks_and_browser_csrf(client):
    user = account(client)
    bad = client.post(
        "/oauth/register",
        json={
            "redirect_uris": ["https://attacker.test"],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
        },
    )
    assert bad.status_code == 400
    client_id = register(client)
    assert authorize(client, client_id, redirect_uri="https://attacker.test").status_code == 400
    wrong_resource = authorize(client, client_id, resource="https://attacker.test")
    assert "error=" in wrong_resource.headers["location"]
    assert parse_qs(urlparse(wrong_resource.headers["location"]).query)["iss"] == [ORIGIN]
    result = authorize(client, client_id)
    request_id = parse_qs(urlparse(result.headers["location"]).query)["request"][0]
    assert (
        client.post(
            "/oauth/consent",
            json={"request_id": request_id, "approve": True},
            headers={**user, "Origin": "https://attacker.test"},
        ).status_code
        == 403
    )
    client.cookies.clear()
    assert client.get("/oauth/consent", params={"request_id": request_id}).status_code == 400
    assert (
        client.post(
            "/oauth/consent", json={"request_id": request_id, "approve": True}, headers={**user, "Origin": ORIGIN}
        ).status_code
        == 400
    )
    assert consent(client, client_id, user, approve=False) is None


def test_expiration_and_deactivated_user(client):
    from hippobox.core.database import get_db
    from hippobox.models.mcp_oauth import OAuthRecord, digest
    from hippobox.models.user import Users

    user = account(client)
    user_id = client.get("/api/v1/auth/me", headers=user).json()["id"]
    client_id = register(client)
    code = consent(client, client_id, user)

    async def expire():
        async with get_db() as db:
            row = await db.get(OAuthRecord, digest(code))
            row.expires = int(time.time()) - 1
            await db.commit()

    client.portal.call(expire)
    assert exchange(client, client_id, code).status_code == 400
    code = consent(client, client_id, user)
    tokens = exchange(client, client_id, code).json()
    client.portal.call(Users.delete, user_id)
    assert client.portal.call(provider.load_access_token, tokens["access_token"]) is None
    assert (
        client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "refresh_token": tokens["refresh_token"],
                "resource": RESOURCE,
            },
        ).status_code
        == 400
    )


def test_user_can_revoke_only_own_connections(client):
    user = account(client)
    other = account(client, "bob")
    client_id = register(client)
    tokens = exchange(client, client_id, consent(client, client_id, user)).json()
    connections = client.get("/oauth/connections", headers=user).json()
    assert len(connections) == 1
    assert client.get("/oauth/connections", headers=other).json() == []
    url = "/oauth/connections/" + connections[0]["id"]
    assert client.delete(url, headers=other).status_code == 404
    assert client.delete(url, headers=user).status_code == 200
    assert client.portal.call(provider.load_access_token, tokens["access_token"]) is None


def test_oversized_registration_and_disabled_discovery(client, monkeypatch):
    assert client.post("/oauth/register", content="x" * 17000).status_code == 413
    assert client.get("/oauth/authorize").headers["x-frame-options"] == "DENY"
    monkeypatch.setattr(SETTINGS, "MCP_OAUTH_ENABLED", False)
    assert client.get("/.well-known/oauth-authorization-server").status_code == 404
