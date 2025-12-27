# HippoBox

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


## MCP settings

### Using with Claude Desktop

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

## Vscode Settings

**launch.json**

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI: Uvicorn",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "hippobox.server:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000"
            ],
            "jinja": true,
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/src/backend/.env",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/src/backend"
            },
            "justMyCode": false,
            "subProcess": true
        }
    ]
}
```

**settings.json**

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}\\\\src\\\\backend\\\\.venv\\\\Scripts\\\\python.exe",
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter",
        "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit"
        }
    },
    "isort.args": ["--profile", "black"]
}
```
