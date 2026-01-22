# HippoBox Agent Guide

## Project overview
- HippoBox is a FastAPI + MCP server for a personal knowledge base with CRUD, semantic search, and MCP tool exposure.
- The backend serves a React/Vite frontend when `src/frontend/dist` exists.

## Repository layout
- `src/backend/hippobox/`: FastAPI app, routers, services, models, core utilities.
- `src/backend/hippobox/migrations/`: Alembic migrations.
- `src/frontend/`: Vite + React UI.
- `docker/`: Docker assets.

## Environment and configuration
- Copy `src/backend/.env.example` to `src/backend/.env` and adjust as needed.
- Embeddings: `OPENAI_API_KEY` is required for embedding calls; configure `EMBEDDING_PROVIDER`/`EMBEDDING_MODEL` as needed.
- Database: SQLite by default (`DB_DRIVER=sqlite+aiosqlite`, `DB_NAME=hippobox.db`). PostgreSQL is optional via env vars.
- Qdrant: local mode by default (`QDRANT_MODE=local`, `QDRANT_PATH=./qdrant_storage`). Use `QDRANT_URL` for Docker/remote.
- Redis: used for auth flows (verification/reset tokens, login throttling, refresh tokens). Ensure Redis is reachable if using auth endpoints.
- API docs: `SWAGGER_ENABLED=true` exposes `/docs`, `/redoc`, `/openapi.json`.

## Run backend (Windows PowerShell)
1. `cd src/backend`
2. `uv sync`
3. `uv run uvicorn hippobox.server:app --reload`
3. Open `http://localhost:8000/docs` if Swagger is enabled.
4. MCP endpoint is available at `http://localhost:8000/mcp`.

## Frontend
- `cd src/frontend`
- `npm install`
- `npm run dev` (watch build to keep `src/frontend/dist` updated for backend serving)
- `npm run dev:vite` (Vite dev server with HMR, default port 5173)
- `npm run build` to produce `src/frontend/dist` (served by backend)
- `npm run preview` to preview the built bundle

## Database migrations
- `cd src/backend`
- `uv run alembic upgrade head`
- `uv run alembic revision --autogenerate -m "your message"`
- Note: The server also creates tables on startup via `init_db()` for local dev.

## Linting and formatting
- `cd src/backend`
- `uv run black .`
- `uv run isort .`
- `uv run flake8 .`

## Tests
- No automated tests found in the repository.

## Coding conventions
- Use async SQLAlchemy sessions from `hippobox.core.database.get_db()`.
- Keep API routes in `hippobox/routers/v1`, business logic in `hippobox/services`, and data models in `hippobox/models`.
- Line length is 120 (Black/Isort configuration).
