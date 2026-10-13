# HippoBox

![HippoBox logo](https://raw.githubusercontent.com/HippoBox/hippobox/main/src/frontend/public/hippobox-banner.png)

HippoBox is a unified FastAPI + FastAPIMcp for managing a personal knowledge base.
It provides CRUD operations for knowledge entries, semantic search powered by embeddings, and MCP tool integration for use in Claude Desktop or other MCP-compatible clients.

### Deploy with Docker

The release image bundles the frontend and backend. Start with the [deployment guide](docs/deployment.md) for PostgreSQL, Redis, Qdrant, and background workers. Existing installations must follow the 0.2 data upgrade steps before starting.

### Overview

See the knowledge entry once it is created in HippoBox.
![Knowledge created](https://raw.githubusercontent.com/HippoBox/hippobox/main/src/frontend/public/guide/step-6.png)

### Hippo Search (VDB)

Use Hippo Search to run VDB searches over your knowledge.
![Hippo Search](https://raw.githubusercontent.com/HippoBox/hippobox/main/src/frontend/public/guide/step-3.png)

### setup MCP

Configure MCP to connect HippoBox with Claude, Cursor, and Codex.
![setup MCP](https://raw.githubusercontent.com/HippoBox/hippobox/main/src/frontend/public/guide/step-4.png)

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

## Development verification

HippoBox keeps its existing UI, API, database and MCP integration while selectively
adopting Blueprint development patterns. See [migration notes](docs/blueprint-migration.md).

```sh
make install
cd src/frontend && npx playwright install chromium && cd ../..
make verify-plan
make verify
```

`make verify` runs isolated backend/browser tests, checks the offline API contract,
and builds and installs the Python package in a temporary environment. Use
`make test-migrations-postgres` for the existing PostgreSQL migration history in a
disposable Docker container. Existing databases are not modified by verification.

API types come from `contracts/openapi.json`, not a running localhost server:
`make contract-export frontend-api-generate` refreshes the reviewed contract and types.

### Start development servers

From the repository root (after `make install`):

```sh
make dev-local
```

This starts FastAPI on `http://127.0.0.1:8000` and Vite on
`http://127.0.0.1:5173`, with vector search disabled and in-memory Redis.
`Ctrl+C` stops both servers. Existing database settings still apply.

Use `make dev` to run both with your configured environment (including Qdrant,
OpenAI and Redis). Use `make backend-dev` or `make frontend-dev` to start only
one server. These targets do not install dependencies or overwrite `.env`.

To start only the backend without an OpenAI key or external Redis:

```sh
make backend-dev-local
```

`make backend-dev` retains the configured environment. With the default
`VDB_ENABLED=true`, set `OPENAI_API_KEY` in `src/backend/.env` first. A missing key
is reported before opening database or vector-store connections. Startup failures
also close any resources that have already been initialized.

Override development ports from the root:

```sh
make dev-local BACKEND_PORT=8001 FRONTEND_PORT=5174
# Or in separate terminals:
make backend-dev-local BACKEND_PORT=8001
make frontend-dev BACKEND_PORT=8001 FRONTEND_PORT=5174
```

The frontend proxy uses `BACKEND_PORT`, so supply the same value when starting
servers separately. Defaults remain 8000/5173. Vite fails when its requested port
is occupied instead of silently selecting a different one.

### Serve the built frontend from the backend

```sh
make install  # first setup
make build
make backend-dev-local BACKEND_PORT=8001
```

Open `http://127.0.0.1:8001`. The build automatically copies Vite output to
`src/backend/hippobox/static/dist`; FastAPI serves those assets and returns
`index.html` for browser routes such as `/app`. API and MCP routes remain separate.
No Vite process is needed for this mode. After frontend edits, run `make build`
again and reload the browser. `make frontend-build` performs just the frontend
build and automatic copy when a Python package rebuild is unnecessary.
