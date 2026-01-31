# HippoBox

![HippoBox logo](https://raw.githubusercontent.com/HippoBox/hippobox/main/src/frontend/public/hippobox-banner.png)

HippoBox is a unified FastAPI + FastAPIMcp for managing a personal knowledge base.
It provides CRUD operations for knowledge entries, semantic search powered by embeddings, and MCP tool integration for use in Claude Desktop or other MCP-compatible clients.

# Running as a package

```bash
pip install hippobox
```

```bash
# Basic execution
hippobox run

# Custom host and port
hippobox run --host 0.0.0.0 --port 8080
```

# Quick Start from Source

## 1. Install uv

**macOS / Linux**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell)**

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

## 2. Setup Project

```bash
cd src/backend
uv sync
```

## 3. Run Server

### macOS / Linux

```bash
cd src/backend
uv run uvicorn hippobox.server:app --reload
```

## 4. Run Frontend

```bash
cd src/frontend
npm install
npm run dev # watch build to keep src/frontend/dist updated for backend serving
npm run dev:vite # Vite dev server with HMR (default 5173)
npm run build # build to src/frontend/dist for backend serving
npm run preview # preview the built bundle
```

# MCP settings

## <img src="https://raw.githubusercontent.com/HippoBox/hippobox/main/src/frontend/src/assets/claude.svg" width="30" height="30" align="center"> Using with Claude Desktop

Add the following to your `claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "hippobox": {
            "command": "uvx",
            "args": [
                "mcp-proxy",
                "--transport",
                "streamablehttp",
                "http://localhost:8000/mcp"
            ],
            "env": {
                "API_ACCESS_TOKEN": "<YOUR_ACCESS_TOKEN>"
            }
        }
    }
}
```

## <img src="https://raw.githubusercontent.com/HippoBox/hippobox/main/src/frontend/src/assets/cursor.svg" width="30" height="30" align="center"> Using with Cursor

Add the following to your Cursor mcp settings:

```json
{
    "mcpServers": {
        "hippobox": {
            "url": "http://localhost:8000/mcp",
            "headers": {
                "Authorization": "Bearer <YOUR_ACCESS_TOKEN>"
            }
        }
    }
}
```

## <img src="https://raw.githubusercontent.com/HippoBox/hippobox/main/src/frontend/src/assets/openai-codex.svg" width="35" height="35" align="center"> Using with Codex

Add the following to your `config.toml`:

```toml
[mcp_servers.hippobox]
startup_timeout_sec = 30
command = "uvx"
args = [
    "mcp-proxy",
    "--transport",
    "streamablehttp",
    "http://localhost:8000/mcp"
]
[mcp_servers.hippobox.env]
API_ACCESS_TOKEN = "<YOUR_ACCESS_TOKEN>"
```
