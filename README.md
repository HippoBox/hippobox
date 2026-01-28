# HippoBox

![HippoBox logo](src/frontend/public/hippobox-banner.png)

HippoBox is a unified FastAPI + FastAPIMcp for managing a personal knowledge base.
It provides CRUD operations for knowledge entries, semantic search powered by embeddings, and MCP tool integration for use in Claude Desktop or other MCP-compatible clients.

# Quick Start

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

### Windows (PowerShell)

```powershell
cd src/backend
uv run uvicorn hippobox.server:app --reload
```

## Frontend

```bash
cd src/frontend
npm install
npm run dev # watch build to keep src/frontend/dist updated for backend serving
npm run dev:vite # Vite dev server with HMR (default 5173)
npm run build # build to src/frontend/dist for backend serving
npm run preview # preview the built bundle
```

## MCP settings

### Using with Claude Desktop

Add the following to your `claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "hippobox": {
            "command": "uvx",
            "args": ["mcp-proxy", "--transport", "streamablehttp", "http://localhost:8000/mcp"],
            "env": {
                "API_ACCESS_TOKEN": "<YOUR_ACCESS_TOKEN>"
            }
        }
    }
}
```

### Using with Cursor

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
