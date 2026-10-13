import os
import sys
from pathlib import Path
from typing import Literal
from urllib.parse import quote, urlsplit

from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr

from hippobox.platform.core.config.base_path import normalize_base_path

load_dotenv()


class Settings(BaseModel):
    def has_multiple_server_workers(self) -> bool:
        """Recognize Uvicorn CLI/env worker counts before enabling terminal animation."""
        values = [os.getenv("WEB_CONCURRENCY", "1"), os.getenv("UVICORN_WORKERS", "1")]
        for index, arg in enumerate(sys.argv):
            if arg == "--workers" and index + 1 < len(sys.argv):
                values.append(sys.argv[index + 1])
            elif arg.startswith("--workers="):
                values.append(arg.partition("=")[2])
        return any(value.isdigit() and int(value) > 1 for value in values)

    # Agent customization note:
    # Add project-wide toggles here first. Keep env names stable for scripts.
    ROOT_DIR: Path = Path(__file__).resolve().parents[2]

    APP_NAME: str = os.getenv("APP_NAME", "Blueprint4FastAPI API")
    APP_MODE: Literal["development", "production"] = os.getenv("APP_MODE", "development")
    APP_LAYOUT: Literal["sidebar", "topnav", "focused"] = Field(
        default=os.getenv("APP_LAYOUT", "sidebar"), validate_default=True
    )
    APP_ENV: str = os.getenv("APP_ENV", "local")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    STARTUP_DISPLAY: Literal["auto", "plain", "off"] = Field(
        default=os.getenv("STARTUP_DISPLAY", "auto"), validate_default=True
    )
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_BASE_PATH: str = os.getenv("APP_BASE_PATH", "")
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:5173")
    SWAGGER_ENABLED: bool = os.getenv("SWAGGER_ENABLED", "true").lower() == "true"
    METRICS_ENABLED: bool = os.getenv("METRICS_ENABLED", "true").lower() == "true"
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    TRUST_PROXY_HEADERS: bool = os.getenv("TRUST_PROXY_HEADERS", "false").lower() == "true"
    TRACING_ENABLED: bool = os.getenv("TRACING_ENABLED", "false").lower() == "true"
    LOGS_ENABLED: bool = os.getenv("LOGS_ENABLED", "false").lower() == "true"
    OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "blueprint4fastapi-backend")
    OTEL_EXPORTER_OTLP_ENDPOINT: str = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "http://localhost:4317",
    )
    OTEL_EXPORTER_OTLP_INSECURE: bool = (
        os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true"
    )
    OTEL_EXPORTER_OTLP_TIMEOUT_SECONDS: int = int(
        os.getenv("OTEL_EXPORTER_OTLP_TIMEOUT_SECONDS", "10")
    )
    OTEL_TRACE_SAMPLE_RATIO: float = float(os.getenv("OTEL_TRACE_SAMPLE_RATIO", "1.0"))

    OBJECT_STORAGE_PROVIDER: Literal["local", "s3", "r2", "supabase"] = Field(
        default=os.getenv("OBJECT_STORAGE_PROVIDER", "local"), validate_default=True
    )
    OBJECT_STORAGE_LOCAL_ROOT: Path = Path(
        os.getenv("OBJECT_STORAGE_LOCAL_ROOT")
        or str(Path(__file__).resolve().parents[3] / "data/object-storage")
    )
    OBJECT_STORAGE_MAX_BYTES: int = Field(
        default=int(os.getenv("OBJECT_STORAGE_MAX_BYTES", "8388608")),
        ge=1,
        le=104857600,
        validate_default=True,
    )
    OBJECT_STORAGE_TIMEOUT_SECONDS: int = Field(
        default=int(os.getenv("OBJECT_STORAGE_TIMEOUT_SECONDS", "10")),
        ge=1,
        le=120,
        validate_default=True,
    )
    OBJECT_STORAGE_S3_ENDPOINT_URL: str = os.getenv("OBJECT_STORAGE_S3_ENDPOINT_URL", "")
    OBJECT_STORAGE_S3_BUCKET: str = os.getenv("OBJECT_STORAGE_S3_BUCKET", "")
    OBJECT_STORAGE_S3_REGION: str = os.getenv("OBJECT_STORAGE_S3_REGION", "")
    OBJECT_STORAGE_S3_ACCESS_KEY_ID: SecretStr = Field(
        default=SecretStr(os.getenv("OBJECT_STORAGE_S3_ACCESS_KEY_ID", "")),
        repr=False,
        exclude=True,
    )
    OBJECT_STORAGE_S3_SECRET_ACCESS_KEY: SecretStr = Field(
        default=SecretStr(os.getenv("OBJECT_STORAGE_S3_SECRET_ACCESS_KEY", "")),
        repr=False,
        exclude=True,
    )
    OBJECT_STORAGE_S3_SESSION_TOKEN: SecretStr = Field(
        default=SecretStr(os.getenv("OBJECT_STORAGE_S3_SESSION_TOKEN", "")),
        repr=False,
        exclude=True,
    )
    OBJECT_STORAGE_S3_ADDRESSING_STYLE: Literal["auto", "path", "virtual"] = Field(
        default=os.getenv("OBJECT_STORAGE_S3_ADDRESSING_STYLE", "auto"), validate_default=True
    )

    STRIPE_ENABLED: bool = os.getenv("STRIPE_ENABLED", "false").lower() == "true"
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_PORTAL_CONFIGURATION_ID: str = os.getenv("STRIPE_PORTAL_CONFIGURATION_ID", "")
    STRIPE_MONTHLY_KRW_PRICE_ID: str = os.getenv("STRIPE_MONTHLY_KRW_PRICE_ID", "")
    STRIPE_MONTHLY_USD_PRICE_ID: str = os.getenv("STRIPE_MONTHLY_USD_PRICE_ID", "")
    STRIPE_ANNUAL_KRW_PRICE_ID: str = os.getenv("STRIPE_ANNUAL_KRW_PRICE_ID", "")
    STRIPE_ANNUAL_USD_PRICE_ID: str = os.getenv("STRIPE_ANNUAL_USD_PRICE_ID", "")
    STRIPE_PLUS_MONTHLY_KRW_PRICE_ID: str = os.getenv("STRIPE_PLUS_MONTHLY_KRW_PRICE_ID", "")
    STRIPE_PLUS_MONTHLY_USD_PRICE_ID: str = os.getenv("STRIPE_PLUS_MONTHLY_USD_PRICE_ID", "")
    STRIPE_PLUS_ANNUAL_KRW_PRICE_ID: str = os.getenv("STRIPE_PLUS_ANNUAL_KRW_PRICE_ID", "")
    STRIPE_PLUS_ANNUAL_USD_PRICE_ID: str = os.getenv("STRIPE_PLUS_ANNUAL_USD_PRICE_ID", "")
    STRIPE_PRO_MONTHLY_KRW_PRICE_ID: str = os.getenv("STRIPE_PRO_MONTHLY_KRW_PRICE_ID", "")
    STRIPE_PRO_MONTHLY_USD_PRICE_ID: str = os.getenv("STRIPE_PRO_MONTHLY_USD_PRICE_ID", "")
    STRIPE_PRO_ANNUAL_KRW_PRICE_ID: str = os.getenv("STRIPE_PRO_ANNUAL_KRW_PRICE_ID", "")
    STRIPE_PRO_ANNUAL_USD_PRICE_ID: str = os.getenv("STRIPE_PRO_ANNUAL_USD_PRICE_ID", "")
    STRIPE_CHECKOUT_SUCCESS_URL: str = os.getenv("STRIPE_CHECKOUT_SUCCESS_URL", "")
    STRIPE_CHECKOUT_CANCEL_URL: str = os.getenv("STRIPE_CHECKOUT_CANCEL_URL", "")

    STRIPE_SETUP_SUCCESS_URL: str = os.getenv("STRIPE_SETUP_SUCCESS_URL", "")
    STRIPE_SETUP_CANCEL_URL: str = os.getenv("STRIPE_SETUP_CANCEL_URL", "")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_ME")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES", "60")
    )
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30")
    )
    LOGIN_FAILED_LIMIT: int = int(os.getenv("LOGIN_FAILED_LIMIT", "5"))
    LOGIN_LOCKED_MINUTES: int = int(os.getenv("LOGIN_LOCKED_MINUTES", "5"))
    DEMO_ENABLED: bool = os.getenv("DEMO_ENABLED", "false").lower() == "true"
    LOGIN_ENABLED: bool = os.getenv("LOGIN_ENABLED", "true").lower() == "true"
    BOOTSTRAP_USER_EMAIL: str = os.getenv("BOOTSTRAP_USER_EMAIL", "demo@example.com")
    BOOTSTRAP_USER_NAME: str = os.getenv("BOOTSTRAP_USER_NAME", "Demo User")

    DB_DRIVER: str = os.getenv("DB_DRIVER", "sqlite+aiosqlite")
    DB_NAME: str = os.getenv("DB_NAME", "template.db")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DATABASE_URL: str | None = None

    REDIS_IN_MEMORY: bool = os.getenv("REDIS_IN_MEMORY", "true").lower() == "true"
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD")
    REDIS_URL: str | None = None

    EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "no-reply@example.com")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", os.getenv("SMTP_USER", ""))
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_STARTTLS: bool = os.getenv("SMTP_USE_STARTTLS", "true").lower() == "true"
    SMTP_USE_SSL: bool = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
    SMTP_TIMEOUT_SECONDS: int = int(os.getenv("SMTP_TIMEOUT_SECONDS", "10"))
    SMTP_VALIDATE_ON_STARTUP: bool = os.getenv("SMTP_VALIDATE_ON_STARTUP", "true").lower() == "true"
    EMAIL_BRAND_NAME: str = os.getenv("EMAIL_BRAND_NAME", "B4A")
    # Celery always uses a real broker, independently of REDIS_IN_MEMORY.
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "")
    CELERY_QUEUE: str = os.getenv("CELERY_QUEUE", "b4fastapi.default")
    CELERY_KEY_PREFIX: str = os.getenv("CELERY_KEY_PREFIX", "b4fastapi:celery:")

    EMAIL_QUEUE_MAX_RETRIES: int = int(os.getenv("EMAIL_QUEUE_MAX_RETRIES", "3"))
    EMAIL_QUEUE_RETRY_DELAY_SECONDS: int = int(os.getenv("EMAIL_QUEUE_RETRY_DELAY_SECONDS", "2"))

    OAUTH_ENABLED: bool = os.getenv("OAUTH_ENABLED", "false").lower() == "true"
    OAUTH_ALLOWED_PROVIDERS: str = os.getenv("OAUTH_ALLOWED_PROVIDERS", "google,github")
    OAUTH_STATE_EXPIRE_MINUTES: int = int(os.getenv("OAUTH_STATE_EXPIRE_MINUTES", "10"))
    OAUTH_FRONTEND_SUCCESS_PATH: str = os.getenv("OAUTH_FRONTEND_SUCCESS_PATH", "/dashboard")
    OAUTH_FRONTEND_FAILURE_PATH: str = os.getenv("OAUTH_FRONTEND_FAILURE_PATH", "/login")

    OAUTH_GOOGLE_CLIENT_ID: str = os.getenv("OAUTH_GOOGLE_CLIENT_ID", "")
    OAUTH_GOOGLE_CLIENT_SECRET: str = os.getenv("OAUTH_GOOGLE_CLIENT_SECRET", "")
    OAUTH_GOOGLE_AUTHORIZE_URL: str = os.getenv(
        "OAUTH_GOOGLE_AUTHORIZE_URL", "https://accounts.google.com/o/oauth2/v2/auth"
    )
    OAUTH_GOOGLE_TOKEN_URL: str = os.getenv(
        "OAUTH_GOOGLE_TOKEN_URL", "https://oauth2.googleapis.com/token"
    )
    OAUTH_GOOGLE_USERINFO_URL: str = os.getenv(
        "OAUTH_GOOGLE_USERINFO_URL", "https://openidconnect.googleapis.com/v1/userinfo"
    )

    OAUTH_GITHUB_CLIENT_ID: str = os.getenv("OAUTH_GITHUB_CLIENT_ID", "")
    OAUTH_GITHUB_CLIENT_SECRET: str = os.getenv("OAUTH_GITHUB_CLIENT_SECRET", "")
    OAUTH_GITHUB_AUTHORIZE_URL: str = os.getenv(
        "OAUTH_GITHUB_AUTHORIZE_URL", "https://github.com/login/oauth/authorize"
    )
    OAUTH_GITHUB_TOKEN_URL: str = os.getenv(
        "OAUTH_GITHUB_TOKEN_URL", "https://github.com/login/oauth/access_token"
    )
    OAUTH_GITHUB_USERINFO_URL: str = os.getenv(
        "OAUTH_GITHUB_USERINFO_URL", "https://api.github.com/user"
    )
    SSE_HEARTBEAT_SECONDS: int = int(os.getenv("SSE_HEARTBEAT_SECONDS", "20"))
    SSE_RETRY_MILLIS: int = int(os.getenv("SSE_RETRY_MILLIS", "5000"))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        object.__setattr__(self, "APP_BASE_PATH", normalize_base_path(self.APP_BASE_PATH))
        if (
            self.APP_BASE_PATH
            and urlsplit(self.APP_BASE_URL).path.rstrip("/") != self.APP_BASE_PATH
        ):
            raise ValueError("APP_BASE_URL must include APP_BASE_PATH")
        self.validate_runtime_mode()
        self.validate_object_storage()

        # When login is globally disabled, auth entry integrations must also stay off.
        if not self.LOGIN_ENABLED:
            object.__setattr__(self, "EMAIL_ENABLED", False)
            object.__setattr__(self, "OAUTH_ENABLED", False)

        if self.DB_DRIVER.startswith("sqlite"):
            db_file = self.ROOT_DIR / self.DB_NAME
            object.__setattr__(self, "DATABASE_URL", f"{self.DB_DRIVER}:///{db_file.as_posix()}")
        else:
            object.__setattr__(
                self,
                "DATABASE_URL",
                (
                    f"{self.DB_DRIVER}://{quote(self.DB_USER, safe='')}"
                    f":{quote(self.DB_PASSWORD, safe='')}"
                    f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
                ),
            )

        if self.REDIS_PASSWORD:
            redis_url = (
                f"redis://:{quote(self.REDIS_PASSWORD, safe='')}"
                f"@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        else:
            redis_url = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        object.__setattr__(self, "REDIS_URL", redis_url)

    def validate_object_storage(self) -> None:
        if self.OBJECT_STORAGE_PROVIDER == "local":
            if not self.OBJECT_STORAGE_LOCAL_ROOT.is_absolute():
                raise ValueError("OBJECT_STORAGE_LOCAL_ROOT must be an absolute path.")
            return
        if not self.OBJECT_STORAGE_S3_BUCKET.strip() or "/" in self.OBJECT_STORAGE_S3_BUCKET:
            raise ValueError("OBJECT_STORAGE_S3_BUCKET must be a bucket name.")
        endpoint = self.OBJECT_STORAGE_S3_ENDPOINT_URL
        if endpoint:
            parsed = urlsplit(endpoint)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "OBJECT_STORAGE_S3_ENDPOINT_URL must be an HTTP(S) endpoint without credentials/query/fragment."
                )
            if self.OBJECT_STORAGE_PROVIDER == "r2" and parsed.path not in {"", "/"}:
                raise ValueError(
                    "R2 endpoint must contain only the account host, without a bucket/path; "
                    "set the bucket separately in OBJECT_STORAGE_S3_BUCKET."
                )
            if self.APP_MODE == "production" and parsed.scheme != "https":
                raise ValueError("Production object storage requires HTTPS.")
        if self.OBJECT_STORAGE_PROVIDER != "r2" and not self.OBJECT_STORAGE_S3_REGION.strip():
            raise ValueError("OBJECT_STORAGE_S3_REGION is required for s3/supabase.")
        has_key = bool(self.OBJECT_STORAGE_S3_ACCESS_KEY_ID.get_secret_value())
        has_secret = bool(self.OBJECT_STORAGE_S3_SECRET_ACCESS_KEY.get_secret_value())
        if has_key != has_secret:
            raise ValueError("Object storage access key and secret key must be set together.")
        if self.OBJECT_STORAGE_S3_SESSION_TOKEN.get_secret_value() and not has_key:
            raise ValueError(
                "Object storage session token requires explicit access and secret keys."
            )
        if self.OBJECT_STORAGE_PROVIDER in {"r2", "supabase"} and (not endpoint or not has_key):
            raise ValueError(
                "r2/supabase require OBJECT_STORAGE_S3_ENDPOINT_URL and S3 access/secret keys."
            )

    def validate_runtime_mode(self) -> None:
        if self.APP_MODE == "production" and not self.LOGIN_ENABLED:
            raise ValueError("APP_MODE=production requires LOGIN_ENABLED=true.")
        if self.APP_MODE == "production":
            minimum_bytes = {"HS256": 32, "HS384": 48, "HS512": 64}.get(self.ALGORITHM)
            key = self.SECRET_KEY
            if (
                minimum_bytes is None
                or key != key.strip()
                or key.upper().startswith("CHANGE_ME")
                or len(key.encode("utf-8")) < minimum_bytes
            ):
                raise ValueError(
                    "Production SECRET_KEY must be a unique random key without surrounding "
                    "whitespace or example placeholders; HS256/HS384/HS512 require at least "
                    "32/48/64 UTF-8 bytes respectively."
                )

    @property
    def celery_broker_url(self) -> str:
        return self.CELERY_BROKER_URL.strip() or self.REDIS_URL

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def oauth_provider_list(self) -> list[str]:
        allowed = [provider.strip().lower() for provider in self.OAUTH_ALLOWED_PROVIDERS.split(",")]
        allowed = [provider for provider in allowed if provider]
        supported = {"google", "github"}
        return [provider for provider in allowed if provider in supported]

    def get_oauth_provider_configs(self) -> dict[str, dict[str, str]]:
        provider_configs: dict[str, dict[str, str]] = {}
        if "google" in self.oauth_provider_list:
            provider_configs["google"] = {
                "client_id": self.OAUTH_GOOGLE_CLIENT_ID,
                "client_secret": self.OAUTH_GOOGLE_CLIENT_SECRET,
                "authorize_url": self.OAUTH_GOOGLE_AUTHORIZE_URL,
                "token_url": self.OAUTH_GOOGLE_TOKEN_URL,
                "userinfo_url": self.OAUTH_GOOGLE_USERINFO_URL,
            }
        if "github" in self.oauth_provider_list:
            provider_configs["github"] = {
                "client_id": self.OAUTH_GITHUB_CLIENT_ID,
                "client_secret": self.OAUTH_GITHUB_CLIENT_SECRET,
                "authorize_url": self.OAUTH_GITHUB_AUTHORIZE_URL,
                "token_url": self.OAUTH_GITHUB_TOKEN_URL,
                "userinfo_url": self.OAUTH_GITHUB_USERINFO_URL,
            }
        return provider_configs

    def get_smtp_validation_errors(self) -> list[str]:
        if not self.EMAIL_ENABLED:
            return []

        errors: list[str] = []
        if not self.SMTP_HOST.strip():
            errors.append("SMTP_HOST is required when EMAIL_ENABLED=true.")
        if self.SMTP_PORT <= 0:
            errors.append("SMTP_PORT must be greater than 0.")
        if not self.EMAIL_FROM.strip():
            errors.append("EMAIL_FROM is required when EMAIL_ENABLED=true.")
        if self.SMTP_USE_SSL and self.SMTP_USE_STARTTLS:
            errors.append("SMTP_USE_SSL and SMTP_USE_STARTTLS cannot both be true.")

        has_username = bool(self.SMTP_USERNAME.strip())
        has_password = bool(self.SMTP_PASSWORD.strip())
        if has_username != has_password:
            errors.append("SMTP_USERNAME and SMTP_PASSWORD must be set together.")

        return errors

    def get_oauth_validation_errors(self) -> list[str]:
        if not self.OAUTH_ENABLED:
            return []

        errors: list[str] = []
        provider_configs = self.get_oauth_provider_configs()
        if not provider_configs:
            errors.append("At least one OAuth provider must be enabled when OAUTH_ENABLED=true.")

        for provider, config in provider_configs.items():
            if not config["client_id"].strip():
                errors.append(f"{provider.upper()} client id is required when OAuth is enabled.")
            if not config["client_secret"].strip():
                errors.append(
                    f"{provider.upper()} client secret is required when OAuth is enabled."
                )

        return errors


