from conftest import account


def test_existing_account_key_and_knowledge_flow(client):
    owner = account(client)
    other = account(client, "bob")
    key = client.post("/api/v1/api_key", headers=owner, json={"name": "legacy-mcp"})
    assert key.status_code == 200, key.text
    legacy = {"Authorization": f"Bearer {key.json()['secret_key']}"}
    assert client.get("/api/v1/auth/me", headers=legacy).json()["name"] == "alice"
    created = client.post(
        "/api/v1/knowledge/",
        headers=legacy,
        json={"title": "Migration", "content": "Existing knowledge", "topic": "Engineering", "tags": ["api"]},
    )
    assert created.status_code == 200, created.text
    kid = created.json()["id"]
    assert client.get(f"/api/v1/knowledge/{kid}", headers=other).status_code == 404
    assert client.get("/api/v1/knowledge/list", headers=other).json() == []
    assert client.get("/api/v1/knowledge/list", headers=owner).json()[0]["id"] == kid
    updated = client.put(f"/api/v1/knowledge/{kid}", headers=owner, json={"content": "Updated"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["content"] == "Updated"
    assert client.delete(f"/api/v1/knowledge/{kid}", headers=owner).status_code == 200
    assert client.get(f"/api/v1/knowledge/{kid}", headers=owner).status_code == 404
    assert (
        client.patch(f"/api/v1/api_key/{key.json()['id']}", headers=owner, json={"is_active": False}).status_code == 200
    )
    assert client.get("/api/v1/auth/me", headers=legacy).status_code == 401


def test_refresh_cookie_and_logout(client):
    headers = account(client)
    refresh = client.post("/api/v1/auth/refresh", json={})
    assert refresh.status_code == 200, refresh.text
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/refresh", json={}).status_code == 401


def test_mcp_transport_lists_tools(client):
    headers = {**account(client), "Accept": "application/json, text/event-stream"}
    response = client.post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        },
    )
    assert response.status_code == 200, response.text
    if response.headers.get("mcp-session-id"):
        headers["mcp-session-id"] = response.headers["mcp-session-id"]
    response = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert response.status_code == 200, response.text
    assert "create_knowledge" in response.text
    assert "search_knowledge" not in response.text


def test_disabled_vector_search(client):
    headers = account(client)
    response = client.get("/api/v1/knowledge/search?query=hello", headers=headers)
    assert response.status_code >= 400
    assert "/api/v1/knowledge/search" not in client.get("/openapi.json").json()["paths"]


def test_request_context_and_spa_api_boundary(client):
    response = client.get("/ping", headers={"X-Request-ID": "migration-check"})
    assert response.headers["x-request-id"] == "migration-check"
    response = client.get("/api/v1/unknown", headers={"Accept": "text/html"})
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


def test_mcp_tool_call_uses_existing_bearer_key(client):
    import json

    owner = account(client)
    key = client.post("/api/v1/api_key", headers=owner, json={"name": "mcp-call"}).json()["secret_key"]
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json, text/event-stream"}
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
                "clientInfo": {"name": "compatibility", "version": "1"},
            },
        },
    )
    assert initialized.status_code == 200, initialized.text
    headers["mcp-session-id"] = initialized.headers["mcp-session-id"]
    client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    response = client.post(
        "/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "create_knowledge", "arguments": {"title": "From MCP", "content": "Tool content"}},
        },
    )
    assert response.status_code == 200, response.text
    message = (
        response.json()
        if "application/json" in response.headers["content-type"]
        else next(json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: "))
    )
    assert not message["result"].get("isError"), response.text
    assert client.get("/api/v1/knowledge/list", headers=owner).json()[0]["title"] == "From MCP"


def test_sqlite_restart_preserves_existing_account_and_key(client):
    from hippobox.core.database import dispose_db, init_db

    headers = account(client)
    key = client.post("/api/v1/api_key", headers=headers, json={"name": "persistent"}).json()["secret_key"]
    before = client.get("/api/v1/auth/me", headers=headers).json()
    client.portal.call(dispose_db)
    client.portal.call(init_db)
    after = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {key}"}).json()
    assert after == before
