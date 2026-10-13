import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette._utils import get_route_path

from hippobox.platform.core.cache.redis import RedisManager
from hippobox.platform.core.config.base_path import PrefixPathMiddleware, validate_frontend_path
from hippobox.platform.core.config.frontend import RuntimeStaticFiles
from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.db.migrations import run_startup_schema_migrations
from hippobox.platform.core.db.session import dispose_db, init_db
from hippobox.platform.core.error import ServiceException, service_exception_to_http
from hippobox.platform.core.mail.service import MAIL_SERVICE
from hippobox.platform.core.object_storage import object_storage_lifespan
from hippobox.platform.core.observability.error_logging import exception_log_level
from hippobox.platform.core.observability.health import HealthCheckResult, ReadinessResponse, get_readiness
from hippobox.platform.core.observability.integration_health import INTEGRATION_HEALTH
from hippobox.platform.core.observability.log_export import setup_log_export
from hippobox.platform.core.observability.logging import configure_request_context_logging, get_logger
from hippobox.platform.core.observability.metrics import setup_metrics
from hippobox.platform.core.observability.request_context import (
    add_request_context_headers,
    reset_request_context,
    resolve_request_id,
    resolve_trace_id,
    set_request_context,
)
from hippobox.platform.core.observability.startup_checks import STARTUP_CHECKS, record_startup_check
from hippobox.platform.core.observability.startup_display import (
    ShutdownDisplay,
    StartupDisplay,
    configure_startup_console,
    show_shutdown_farewell,
    shutdown_step,
    startup_phase,
    startup_step,
)
from hippobox.platform.core.observability.tracing import setup_tracing
from hippobox.platform.core.openapi import register_openapi_contracts
from hippobox.platform.models.user import UserResponse, Users
from hippobox.platform.routers.v1 import admin, api_key, auth, billing, billing_webhook, events, inbox, inquiry
from hippobox.platform.services.admin import DEMO_SNAPSHOTS
from hippobox.platform.services.billing import BillingService
from hippobox.platform.utils.token import create_access_token

logger = get_logger("hippobox.platform.main")
BOOTSTRAP_USER: UserResponse | None = None


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ServiceException)
    async def service_exception_handler(request: Request, exc: ServiceException):
        http_exc = service_exception_to_http(exc)
        logger.log(
            exception_log_level(http_exc.status_code, error_code=exc.code.error),
            "Service exception handled globally (method=%s, path=%s, status=%s, code=%s).",
            request.method,
            request.url.path,
            http_exc.status_code,
            exc.code.error,
        )
        return JSONResponse(status_code=http_exc.status_code, content={"detail": http_exc.detail})

    @app.exception_handler(Exception)
    async def default_exception_handler(_request, _exc):
        if isinstance(_exc, HTTPException):
            logger.log(
                exception_log_level(_exc.status_code),
                "HTTP exception handled globally (status=%s, detail=%s).",
                _exc.status_code,
                _exc.detail,
            )
            return JSONResponse(status_code=_exc.status_code, content={"detail": _exc.detail})
        logger.exception("Unhandled server exception.")
        return JSONResponse(
            status_code=500,
            content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred."},
        )


class AppConfigResponse(BaseModel):
    api_base_path: str
    app_mode: Literal["development", "production"]
    app_layout: Literal["sidebar", "topnav", "focused"] = "sidebar"
    demo_enabled: bool = False
    login_enabled: bool
    frontend_base_path: str
    email_enabled: bool
    oauth_enabled: bool
    billing_enabled: bool
    oauth_providers: list[str]
    bootstrap_user: UserResponse | None = None
    bootstrap_access_token: str | None = None


@asynccontextmanager
async def application_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global BOOTSTRAP_USER
    await DEMO_SNAPSHOTS.reset()
    await INTEGRATION_HEALTH.reset()
    STARTUP_CHECKS.clear()
    try:
        SETTINGS.validate_runtime_mode()
        with startup_step("redis"):
            await asyncio.wait_for(RedisManager.verify_startup(), timeout=5)
        with startup_step("oauth", success="Configured"):
            if not SETTINGS.OAUTH_ENABLED:
                logger.info("OAuth integration is disabled.")
            else:
                logger.info(
                    "OAuth integration enabled (providers=%s).",
                    ",".join(SETTINGS.oauth_provider_list),
                )

            oauth_errors = SETTINGS.get_oauth_validation_errors()
            if oauth_errors:
                raise RuntimeError("Invalid OAuth configuration: " + " ".join(oauth_errors))
            if SETTINGS.OAUTH_ENABLED:
                logger.info("OAuth configuration validation succeeded.")

            record_startup_check("oauth", "configured" if SETTINGS.OAUTH_ENABLED else "disabled")
        with startup_step(
            "email",
            success="Verified" if SETTINGS.SMTP_VALIDATE_ON_STARTUP else "Configured",
            detail="" if SETTINGS.SMTP_VALIDATE_ON_STARTUP else "Connection check skipped",
        ):
            await MAIL_SERVICE.initialize()
        record_startup_check(
            "email",
            "disabled"
            if not SETTINGS.EMAIL_ENABLED
            else "ok"
            if SETTINGS.SMTP_VALIDATE_ON_STARTUP
            else "configured",
        )
        with startup_step("billing"):
            await BillingService().initialize()
        record_startup_check("billing", "ok" if SETTINGS.STRIPE_ENABLED else "disabled")
        with startup_step("database", success="Ready"):
            startup_phase("database", "Migrating…")
            await run_startup_schema_migrations(SETTINGS.DATABASE_URL)
            logger.info("Database schema migration check complete (target=head).")
            startup_phase("database", "Initializing…")
            await init_db()
            logger.info("Database initialization complete.")
            BOOTSTRAP_USER = None
            if not SETTINGS.LOGIN_ENABLED:
                from hippobox.platform.services.bootstrap import BootstrapService

                BOOTSTRAP_USER = await BootstrapService().initialize()
        logger.info("Application startup sequence complete.")
        yield
    finally:
        await DEMO_SNAPSHOTS.reset()
        await INTEGRATION_HEALTH.reset()
        try:
            with shutdown_step("database"):
                await dispose_db()
        finally:
            with shutdown_step("redis"):
                await RedisManager.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # The storage client is also closed if subsequent application startup fails.
    async with AsyncExitStack() as stack:
        with StartupDisplay(SETTINGS).activate():
            await stack.enter_async_context(object_storage_lifespan(app, SETTINGS))
            await stack.enter_async_context(application_lifespan(app))
        try:
            yield
        finally:
            with ShutdownDisplay(SETTINGS, redis_open=RedisManager._client is not None).activate():
                await stack.aclose()
    show_shutdown_farewell(SETTINGS)


def create_app() -> FastAPI:
    static_dist_dir = (Path(__file__).resolve().parent / "static" / "dist").resolve()
    log_level_name = SETTINGS.LOG_LEVEL.upper()
    log_level_value = logging.getLevelName(log_level_name)
    if not isinstance(log_level_value, int):
        log_level_name = "INFO"
        log_level_value = logging.INFO

    logging.getLogger("uvicorn.error").setLevel(log_level_value)
    logging.getLogger("uvicorn.access").setLevel(log_level_value)
    logging.getLogger("uvicorn").setLevel(log_level_value)
    configure_request_context_logging()
    configure_startup_console(SETTINGS)
    setup_log_export()

    validate_frontend_path(static_dist_dir, SETTINGS.APP_BASE_PATH)
    app = FastAPI(
        root_path=SETTINGS.APP_BASE_PATH,
        title=SETTINGS.APP_NAME,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if SETTINGS.SWAGGER_ENABLED else None,
        redoc_url="/redoc" if SETTINGS.SWAGGER_ENABLED else None,
        openapi_url="/openapi.json" if SETTINGS.SWAGGER_ENABLED else None,
    )

    logger.info("App log level set to %s.", log_level_name)

    app.add_middleware(PrefixPathMiddleware, base_path=SETTINGS.APP_BASE_PATH)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=SETTINGS.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Trace-ID"],
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = resolve_request_id(request)
        trace_id = resolve_trace_id(request)
        tokens = set_request_context(request_id=request_id, trace_id=trace_id)
        try:
            response = await call_next(request)
            add_request_context_headers(
                response,
                request_id=request_id,
                trace_id=trace_id,
            )
            return response
        finally:
            reset_request_context(tokens)

    register_exception_handlers(app)

    @app.get("/ping")
    async def ping():
        return {"status": "ok", "message": "pong"}

    @app.get("/health/live", response_model=HealthCheckResult)
    async def health_live():
        return HealthCheckResult(status="ok")

    @app.get(
        "/health/ready",
        response_model=ReadinessResponse,
        responses={
            status.HTTP_503_SERVICE_UNAVAILABLE: {
                "model": ReadinessResponse,
                "description": "One or more required dependencies are unavailable",
            },
        },
    )
    async def health_ready():
        readiness = await get_readiness()
        if readiness.status != "ok":
            return JSONResponse(status_code=503, content=readiness.model_dump())
        return readiness

    @app.get("/config", response_model=AppConfigResponse)
    async def config(response: Response):
        response.headers["Cache-Control"] = "no-store"
        bootstrap_user = (
            await Users.get_user_response_by_id(BOOTSTRAP_USER.id)
            if not SETTINGS.LOGIN_ENABLED and BOOTSTRAP_USER
            else None
        )
        bootstrap_token = (
            create_access_token(subject=str(bootstrap_user.id), email=bootstrap_user.email)
            if bootstrap_user
            else None
        )
        return {
            "api_base_path": "/api/v1",
            "app_mode": SETTINGS.APP_MODE,
            "app_layout": SETTINGS.APP_LAYOUT,
            "demo_enabled": SETTINGS.DEMO_ENABLED,
            "login_enabled": SETTINGS.LOGIN_ENABLED,
            "frontend_base_path": SETTINGS.APP_BASE_PATH,
            "email_enabled": SETTINGS.EMAIL_ENABLED,
            "oauth_enabled": SETTINGS.LOGIN_ENABLED and SETTINGS.OAUTH_ENABLED,
            "billing_enabled": SETTINGS.STRIPE_ENABLED,
            "oauth_providers": SETTINGS.oauth_provider_list
            if SETTINGS.LOGIN_ENABLED and SETTINGS.OAUTH_ENABLED
            else [],
            "bootstrap_user": bootstrap_user,
            "bootstrap_access_token": bootstrap_token,
        }

    setup_metrics(app)
    setup_tracing(app)

    app.include_router(inbox.router, prefix="/api/v1/inbox", tags=["Inbox"])
    app.include_router(inquiry.router, prefix="/api/v1/inquiries", tags=["Inquiries"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(api_key.router, prefix="/api/v1/api-keys", tags=["API Keys"])
    app.include_router(billing_webhook.router, prefix="/api/v1/billing", tags=["Billing"])
    app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing"])
    app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])

    if static_dist_dir.exists():
        frontend = RuntimeStaticFiles(
            static_dist_dir, SETTINGS.APP_BASE_PATH, SETTINGS.APP_BASE_URL
        )
        app.mount("/", frontend, name="frontend")

        @app.exception_handler(404)
        async def spa_fallback(request: Request, exc):
            accepts_html = "text/html" in request.headers.get("accept", "")
            route_path = get_route_path(request.scope)
            is_api_path = route_path.startswith("/api/")
            # Missing public documents/assets must remain 404 (including deleted
            # discovery URLs); never disguise them as the application shell.
            is_document_path = (
                route_path == "/about"
                or route_path.startswith("/about/")
                or bool(Path(route_path).suffix)
            )
            if (
                request.method in {"GET", "HEAD"}
                and accepts_html
                and not is_api_path
                and not is_document_path
            ):
                index_path = static_dist_dir / "index.html"
                if index_path.exists():
                    return await frontend.document_response(index_path, request.scope)

            # Preserve API error payload shape for domain 404 responses.
            if is_api_path:
                detail = getattr(exc, "detail", "Not Found")
                return JSONResponse(status_code=404, content={"detail": detail})

            return JSONResponse(status_code=404, content={"detail": "Not Found"})

    register_openapi_contracts(app)
    return app


app = create_app()
