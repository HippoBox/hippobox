from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from hippobox.platform.core.observability.integration_health import IntegrationCheck
from hippobox.platform.core.observability.startup_checks import StartupCheck


class AdminConnection(BaseModel):
    id: Literal["server", "database", "cache", "object_storage"]
    technology: Literal[
        "fastapi",
        "sqlite",
        "postgresql",
        "mysql",
        "mariadb",
        "database",
        "redis",
        "memory",
        "local",
        "s3",
        "r2",
        "supabase",
    ]
    status: Literal["ok", "failed", "timeout"]
    latency_ms: float | None = None
    host: str | None = None
    port: int | None = None
    transport: Literal["filesystem", "https", "http"] | None = None
    probe: Literal["local_io", "bucket_access"] | None = None
    checked_at: datetime | None = None


class AdminEnvironmentValues(BaseModel):
    APP_MODE: Literal["development", "production"]
    EMAIL_ENABLED: bool
    LOGIN_ENABLED: bool
    OAUTH_ENABLED: bool
    STRIPE_ENABLED: bool
    REDIS_IN_MEMORY: bool


class AdminEnvironment(BaseModel):
    app_mode: Literal["development", "production"]
    email_enabled: bool
    login_enabled: bool
    oauth_enabled: bool
    oauth_providers: list[str]
    billing_configured: bool
    billing_enabled: bool
    billing_mode: Literal["disabled", "test", "live"]
    admin_access: Literal["admin_only"] = "admin_only"
    developer_enabled: bool
    redis_in_memory: bool


class AdminStatusResponse(BaseModel):
    status: Literal["ok", "degraded"]
    checked_at: datetime
    connections: list[AdminConnection]
    environment: AdminEnvironment
    environment_values: AdminEnvironmentValues
    startup_checks: dict[str, StartupCheck]
    integration_checks: dict[str, IntegrationCheck]
