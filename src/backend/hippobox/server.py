import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi_mcp import FastApiMCP

from hippobox.core.bootstrap_admin import ensure_admin_for_login_disabled, ensure_default_admin_from_settings
from hippobox.core.database import dispose_db, init_db
from hippobox.core.logging_config import setup_logger
from hippobox.core.redis import RedisManager
from hippobox.core.settings import SETTINGS
from hippobox.rag.embedding import Embedding
from hippobox.rag.qdrant import Qdrant
from hippobox.routers.v1 import admin, api_key, auth, knowledge, topic
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
    await ensure_admin_for_login_disabled()
    await ensure_default_admin_from_settings()

    if SETTINGS.VDB_ENABLED:
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
    else:
        app.state.QDRANT = None
        app.state.EMBEDDING = None
        log.info("VDB disabled; skipping Qdrant and embedding initialization")

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
    app.include_router(
        topic.router,
        prefix="/api/v1/topic",
        tags=["Topic"],
    )
    app.include_router(
        admin.router,
        prefix="/api/v1/admin",
        tags=["Admin"],
    )

    @app.get("/ping", operation_id="ping_tool")
    async def ping():
        return {"status": "ok", "message": "pong"}

    include_operations = [
        "ping_tool",
        *[op.value for op in OperationID if SETTINGS.VDB_ENABLED or op != OperationID.search_knowledge],
    ]

    mcp = FastApiMCP(
        app,
        include_operations=include_operations,
    )
    mcp.mount_http()
    log.info("MCP tools registered.")
    log.info("registered tools: ", mcp.tools)

    def normalize_base_path(value: str) -> str:
        path = value.strip()
        if not path:
            return "/"
        if not path.startswith("/"):
            path = f"/{path}"
        path = path.rstrip("/")
        return path or "/"

    frontend_base_path = normalize_base_path(SETTINGS.FRONTEND_BASE_PATH)
    static_files_dist = (SETTINGS.ROOT_DIR / "dist").resolve()

    @app.get("/config")
    async def app_config():
        return {
            "login_enabled": SETTINGS.LOGIN_ENABLED,
            "email_enabled": SETTINGS.EMAIL_ENABLED,
            "frontend_base_path": frontend_base_path,
            "api_base_path": "/api/v1",
        }

    if static_files_dist.exists():
        if frontend_base_path != "/":

            @app.get("/")
            async def frontend_base_redirect():
                return RedirectResponse(url=frontend_base_path)

        app.mount(
            frontend_base_path,
            StaticFiles(directory=static_files_dist, html=True),
            name="frontend",
        )

        @app.exception_handler(404)
        async def spa_fallback(request, exc):
            accepts_html = "text/html" in request.headers.get("accept", "")
            is_frontend_path = frontend_base_path == "/" or request.url.path.startswith(frontend_base_path)

            if request.method in {"GET", "HEAD"} and accepts_html and is_frontend_path:
                index_path = static_files_dist / "index.html"
                if index_path.exists():
                    return FileResponse(index_path)

            detail = getattr(exc, "detail", "Not Found")
            return JSONResponse(status_code=404, content={"detail": detail})

    else:
        log.info("Frontend dist not found. Run npm install && npm run build in ./src/frontend.")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app", host="0.0.0.0", port=8000, reload=True)
