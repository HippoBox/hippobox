import asyncio
import hashlib
import hmac
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from time import monotonic
from typing import TypeVar, cast
from urllib.parse import urlsplit

from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.db.session import get_engine
from hippobox.platform.core.error.admin_exception import AdminErrorCode, AdminException
from hippobox.platform.core.mail.service import MAIL_SERVICE
from hippobox.platform.core.object_storage import ObjectStorage
from hippobox.platform.core.observability.health import check_dependencies
from hippobox.platform.core.observability.integration_health import INTEGRATION_HEALTH
from hippobox.platform.core.observability.service import observe_service
from hippobox.platform.core.observability.startup_checks import STARTUP_CHECKS, StartupCheck
from hippobox.platform.models.admin import (
    AdminConnection,
    AdminEnvironment,
    AdminEnvironmentValues,
    AdminStatusResponse,
)
from hippobox.platform.models.user import (
    AdminUserListResponse,
    AdminUserResponse,
    UserRole,
    UserRoleStatsResponse,
    Users,
)
from hippobox.platform.services.billing import BillingService


class AdminService:
    @observe_service("admin.demo_users")
    async def demo_users(
        self,
        *,
        page: int,
        page_size: int,
        search: str,
        role: UserRole | None,
        is_active: bool | None,
    ) -> AdminUserListResponse:
        require_demo_enabled()

        async def load() -> list[AdminUserResponse]:
            rows = await Users.list_demo_user_projection()
            items = []
            for row in rows:
                token = hmac.new(
                    SETTINGS.SECRET_KEY.encode(),
                    f"admin-demo-user:{row['id']}".encode(),
                    hashlib.sha256,
                ).hexdigest()[:12]
                items.append(
                    AdminUserResponse(
                        id=int(token, 16),
                        name=f"User {token}",
                        email=f"{token}@demo.invalid",
                        role=row["role"],
                        is_active=row["is_active"],
                        is_verified=row["is_verified"],
                        created_at=_demo_day(row["created_at"]),
                        last_login_at=_demo_day(row["last_login_at"]),
                        login_providers=row["login_providers"],
                    )
                )
            return items

        items = await DEMO_SNAPSHOTS.get("users", load)
        require_demo_enabled()
        summary = UserRoleStatsResponse(
            total_users=len(items),
            active_users=sum(item.is_active for item in items),
            admin_users=sum(item.role == UserRole.ADMIN for item in items),
            manager_users=sum(item.role == UserRole.MANAGER for item in items),
        )
        needle = search.strip().casefold()
        filtered = [
            item
            for item in items
            if (not needle or needle in item.name.casefold() or needle in item.email)
            and (role is None or item.role == role)
            and (is_active is None or item.is_active == is_active)
        ]
        return AdminUserListResponse(
            items=filtered[(page - 1) * page_size : page * page_size],
            total=len(filtered),
            page=page,
            page_size=page_size,
            summary=summary,
        )

    @observe_service("admin.demo_status")
    async def demo_status(self, storage: ObjectStorage | None = None) -> AdminStatusResponse:
        require_demo_enabled()

        async def load() -> AdminStatusResponse:
            result = (await self.status(storage)).model_copy(deep=True)
            for connection in result.connections:
                connection.host = None
                connection.port = None
            return result

        result = await DEMO_SNAPSHOTS.get("status", load)
        require_demo_enabled()
        return result.model_copy(deep=True)

    @observe_service("admin.status")
    async def status(self, storage: ObjectStorage | None = None) -> AdminStatusResponse:
        try:
            billing_service = BillingService()
            billing = billing_service.config()

            async def storage_probe() -> None:
                if storage is None:
                    raise RuntimeError("Storage is not initialized")
                await storage.check_connection()

            checks, email_check, billing_check, storage_check = await asyncio.gather(
                check_dependencies(),
                INTEGRATION_HEALTH.check(
                    "email", SETTINGS.EMAIL_ENABLED, MAIL_SERVICE.check_connection
                ),
                INTEGRATION_HEALTH.check(
                    "billing", billing.enabled, billing_service.check_connection
                ),
                INTEGRATION_HEALTH.check("object_storage", True, storage_probe),
            )
            transport, storage_port = "filesystem", None
            if SETTINGS.OBJECT_STORAGE_PROVIDER != "local":
                transport = "https"
                storage_port = 443
                endpoint = SETTINGS.OBJECT_STORAGE_S3_ENDPOINT_URL
                if endpoint:
                    try:
                        parsed = urlsplit(endpoint)
                        transport = parsed.scheme if parsed.scheme in {"https", "http"} else None
                        storage_port = (
                            (parsed.port or (443 if transport == "https" else 80))
                            if transport
                            else None
                        )
                    except ValueError:
                        transport, storage_port = None, None
            engine = get_engine()
            dialect = engine.dialect.name
            database = (
                dialect if dialect in {"sqlite", "postgresql", "mysql", "mariadb"} else "database"
            )
            cache_host, cache_port = None, None
            if not SETTINGS.REDIS_IN_MEMORY:
                try:
                    redis_url = urlsplit(SETTINGS.REDIS_URL)
                    if redis_url.scheme in {"redis", "rediss"}:
                        cache_host, cache_port = redis_url.hostname, redis_url.port or 6379
                except ValueError:
                    pass  # Failed connectivity is reported without returning malformed secrets.
            return AdminStatusResponse(
                status="ok"
                if all(check.status == "ok" for check in checks.values())
                and all(
                    check.status in {"ok", "disabled"}
                    for check in (email_check, billing_check, storage_check)
                )
                else "degraded",
                checked_at=datetime.now(UTC),
                integration_checks={"email": email_check, "billing": billing_check},
                startup_checks={
                    name: STARTUP_CHECKS.get(name, StartupCheck(status="unverified")).model_copy()
                    for name in ("email", "billing", "oauth")
                },
                connections=[
                    AdminConnection(id="server", technology="fastapi", status="ok"),
                    AdminConnection(
                        id="database",
                        technology=database,
                        host=engine.url.host,
                        port=engine.url.port
                        or {"postgresql": 5432, "mysql": 3306, "mariadb": 3306}.get(dialect),
                        **checks["database"].model_dump(),
                    ),
                    AdminConnection(
                        id="cache",
                        technology="memory" if SETTINGS.REDIS_IN_MEMORY else "redis",
                        host=cache_host,
                        port=cache_port,
                        **checks["redis"].model_dump(),
                    ),
                    AdminConnection(
                        id="object_storage",
                        technology=SETTINGS.OBJECT_STORAGE_PROVIDER,
                        status=storage_check.status,
                        latency_ms=storage_check.latency_ms,
                        checked_at=storage_check.checked_at,
                        transport=transport,
                        port=storage_port,
                        probe="local_io"
                        if SETTINGS.OBJECT_STORAGE_PROVIDER == "local"
                        else "bucket_access",
                    ),
                ],
                environment_values=AdminEnvironmentValues(
                    APP_MODE=SETTINGS.APP_MODE,
                    EMAIL_ENABLED=SETTINGS.EMAIL_ENABLED,
                    LOGIN_ENABLED=SETTINGS.LOGIN_ENABLED,
                    OAUTH_ENABLED=SETTINGS.OAUTH_ENABLED,
                    STRIPE_ENABLED=SETTINGS.STRIPE_ENABLED,
                    REDIS_IN_MEMORY=SETTINGS.REDIS_IN_MEMORY,
                ),
                environment=AdminEnvironment(
                    app_mode=SETTINGS.APP_MODE,
                    email_enabled=SETTINGS.EMAIL_ENABLED,
                    login_enabled=SETTINGS.LOGIN_ENABLED,
                    oauth_enabled=SETTINGS.LOGIN_ENABLED and SETTINGS.OAUTH_ENABLED,
                    oauth_providers=SETTINGS.oauth_provider_list
                    if SETTINGS.LOGIN_ENABLED and SETTINGS.OAUTH_ENABLED
                    else [],
                    billing_configured=SETTINGS.STRIPE_ENABLED,
                    billing_enabled=billing.enabled,
                    billing_mode=("live" if billing.livemode else "test")
                    if billing.enabled
                    else "disabled",
                    developer_enabled=SETTINGS.APP_MODE == "development",
                    redis_in_memory=SETTINGS.REDIS_IN_MEMORY,
                ),
            )
        except Exception as exc:
            raise AdminException(AdminErrorCode.STATUS_FAILED) from exc


DemoSnapshot = TypeVar("DemoSnapshot")


class AdminDemoSnapshots:
    """Only sanitized data is retained; coalesce public traffic per process."""

    def __init__(self) -> None:
        self.cache: dict[str, tuple[float, object]] = {}
        self.pending: dict[str, asyncio.Task] = {}

    async def get(self, key: str, load: Callable[[], Awaitable[DemoSnapshot]]) -> DemoSnapshot:
        cached = self.cache.get(key)
        if cached and monotonic() - cached[0] < 30:
            return cast(DemoSnapshot, cached[1])
        task = self.pending.get(key)
        if task is None or task.done():

            async def run() -> DemoSnapshot:
                result = await asyncio.wait_for(load(), timeout=7)
                self.cache[key] = (monotonic(), result)
                return result

            task = asyncio.create_task(run())
            self.pending[key] = task
        try:
            return await asyncio.wait_for(asyncio.shield(task), 8)
        except Exception as exc:
            raise AdminException(AdminErrorCode.DEMO_FAILED) from exc

    async def reset(self) -> None:
        tasks = list(self.pending.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.pending.clear()
        self.cache.clear()


DEMO_SNAPSHOTS = AdminDemoSnapshots()


def require_demo_enabled() -> None:
    if not SETTINGS.DEMO_ENABLED:
        raise AdminException(AdminErrorCode.DEMO_DISABLED)


def _demo_day(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return value.replace(hour=0, minute=0, second=0, microsecond=0)
