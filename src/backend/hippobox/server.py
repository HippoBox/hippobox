import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi_mcp import FastApiMCP

from hippobox.core.database import dispose_db, init_db
from hippobox.core.logging_config import setup_logger
from hippobox.core.redis import RedisManager
from hippobox.core.settings import SETTINGS
from hippobox.rag.embedding import Embedding
from hippobox.rag.qdrant import Qdrant
from hippobox.routers.v1 import api_key, auth, knowledge
from hippobox.routers.v1.knowledge import OperationID

log = logging.getLogger("hippobox")

print(
    "  _    _ _                   ____            \n"
    " | |  | (_)                 |  _ \\           \n"
    " | |__| |_ _ __  _ __   ___ | |_) | _____  __\n"
    " |  __  | | '_ \\| '_ \\ / _ \\|  _ < / _ \\/\\/ /\n"
    " | |  | | | |_) | |_) | (_) | |_) | (_) >  < \n"
    " |_|  |_|_| .__/| .__/ \\___/|____/ \\___/_/\\_\\\n"
    "          | |   | |                           \n"
    "          |_|   |_|                           \n"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger()

    app.state.SETTINGS = SETTINGS
    log.info(f"SETTINGS Loaded | ROOT_DIR={SETTINGS.ROOT_DIR}")

    await init_db()
    log.info("Database initialized")

    try:
        qdrant = Qdrant()
        app.state.QDRANT = qdrant
        log.info("Qdrant client initialized")

    except Exception as e:
        log.error(f"Qdrant initialization failed: {e}")
        raise

    try:
        embedding = Embedding()
        app.state.EMBEDDING = embedding
        log.info("Embedding client initialized")

    except Exception as e:
        log.error(f"Embedding initialization failed: {e}")
        raise

    log.info("HippoBox Server Lifespan Startup")
    try:
        yield
    finally:
        await dispose_db()
        await RedisManager.close()
        log.info("HippoBox Server Lifespan Shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="HippoBox MCP Server",
        version="0.1.0",
        description="Unified FastAPI + MCP server for Knowledge Store & RAG",
        lifespan=lifespan,
        docs_url="/docs" if SETTINGS.SWAGGER_ENABLED else None,
        redoc_url="/redoc" if SETTINGS.SWAGGER_ENABLED else None,
        openapi_url="/openapi.json" if SETTINGS.SWAGGER_ENABLED else None,
    )

    @app.exception_handler(Exception)
    async def default_handler(request, exc):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_ERROR",
                "message": "An internal server error occurred",
            },
        )

    app.include_router(
        auth.router,
        prefix="/api/v1/auth",
        tags=["Auth"],
    )

    app.include_router(
        api_key.router,
        prefix="/api/v1/api_key",
        tags=["Api Key"],
    )

    app.include_router(
        knowledge.router,
        prefix="/api/v1/knowledge",
        tags=["Knowledge"],
    )

    @app.get("/ping", operation_id="ping_tool")
    async def ping():
        return {"status": "ok", "message": "pong"}

    mcp = FastApiMCP(
        app,
        include_operations=[
            "ping_tool",
            *[op.value for op in OperationID],
        ],
    )
    mcp.mount_http()
    log.info("MCP tools registered.")
    log.info("registered tools: ", mcp.tools)

    frontend_dist = (SETTINGS.ROOT_DIR.parent / "frontend" / "dist").resolve()
    if frontend_dist.exists():

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(full_path: str):
            file_path = (frontend_dist / full_path).resolve()
            try:
                file_path.relative_to(frontend_dist)
            except ValueError:
                raise HTTPException(status_code=404, detail="Not Found")

            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(frontend_dist / "index.html")

    else:
        log.info("Frontend dist not found. Run npm install && npm run build in ./src/frontend.")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app", host="0.0.0.0", port=8000, reload=True)
