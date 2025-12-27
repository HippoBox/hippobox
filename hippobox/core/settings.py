import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    ROOT_DIR: Path = Path(__file__).resolve().parents[2]

    # ----------------------------------------
    # API Docs (Swagger/OpenAPI)
    # ----------------------------------------
    SWAGGER_ENABLED: bool = os.getenv("SWAGGER_ENABLED", "true").lower() == "true"

    # ----------------------------------------
    # LLM / Embedding
    # ----------------------------------------
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "openai")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # ----------------------------------------
    # Auth
    # ----------------------------------------
    # TODO: development-only option
    SECRET_KEY: str = "HIPPOBOX_DEV_SECRET"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    LOGIN_FAILED_LIMIT: int = 5
    LOGIN_LOCKED_MINUTES: int = 15

    # ----------------------------------------
    # SQL Database (raw env)
    # ----------------------------------------
    DB_DRIVER: str = os.getenv("DB_DRIVER", "sqlite+aiosqlite")
    DB_NAME: str = os.getenv("DB_NAME", "hippobox.db")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DATABASE_URL: str | None = None

    # ----------------------------------------
    # Qdrant
    # ----------------------------------------
    QDRANT_MODE: str = os.getenv("QDRANT_MODE", "local")
    QDRANT_PATH: str = os.getenv("QDRANT_PATH", "qdrant_storage")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_LOCAL_PATH: Path | None = None

    # ----------------------------------------
    # Redis
    # ----------------------------------------
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD", None)
    REDIS_URL: str | None = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.DB_DRIVER.startswith("sqlite"):
            db_file = self.ROOT_DIR / self.DB_NAME
            object.__setattr__(self, "DATABASE_URL", f"{self.DB_DRIVER}:///{db_file.as_posix()}")
        else:
            object.__setattr__(
                self,
                "DATABASE_URL",
                (
                    f"{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}"
                    f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
                ),
            )

        if self.QDRANT_MODE.lower() == "local":
            object.__setattr__(
                self,
                "QDRANT_LOCAL_PATH",
                (self.ROOT_DIR / self.QDRANT_PATH).resolve(),
            )

        if self.REDIS_PASSWORD:
            redis_url = f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        else:
            redis_url = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        object.__setattr__(self, "REDIS_URL", redis_url)


SETTINGS = Settings()
