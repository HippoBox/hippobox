import hashlib
import secrets
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column

from hippobox.core.database import Base, get_db


class APIKey(Base):
    __tablename__ = "api_key"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(nullable=False)

    access_key: Mapped[str] = mapped_column(nullable=False, index=True)
    secret_hash: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)

    total_requests: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class APIKeyModel(BaseModel):
    id: int = Field(..., description="Unique identifier of the API Key")

    user_id: int = Field(..., description="Owner's user identifier")
    name: str = Field(..., description="User defined name for the key")

    access_key: str = Field(..., description="Prefix of the key for identification")
    secret_hash: str = Field(..., description="Hashed value of the key")

    total_requests: int = Field(..., description="Total number of requests made using this key")
    is_active: bool = Field(..., description="Whether the key is active")
    last_used_at: datetime | None = Field(None, description="Last usage timestamp")

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class APIKeyForm(BaseModel):
    name: str = Field(..., description="A recognizable name for the API Key (e.g. My Laptop)")
    user_id: int = Field(..., description="User ID to associate with this key")


class APIKeyCreatedResponse(BaseModel):
    id: int
    name: str
    access_key: str
    secret_key: str = Field(..., description="RAW SECRET KEY - Shown only once!")
    total_requests: int = Field(..., description="Total number of requests made using this key")
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyResponse(BaseModel):
    id: int
    user_id: int
    name: str
    access_key: str = Field(..., description="Prefix of the key")
    total_requests: int = Field(..., description="Total number of requests made using this key")
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyUpdate(BaseModel):
    name: str | None = Field(None, description="Updated name")
    is_active: bool | None = Field(None, description="Update active status")


class APIKeyTable:
    async def create(self, form: APIKeyForm) -> APIKeyCreatedResponse:
        raw_key = f"sk-{secrets.token_urlsafe(35)}"

        hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()

        prefix = raw_key[:10]

        async with get_db() as db:
            api_key = APIKey(
                user_id=form.user_id,
                name=form.name,
                access_key=prefix,
                secret_hash=hashed_key,
                total_requests=0,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(api_key)
            await db.commit()
            await db.refresh(api_key)

            return APIKeyCreatedResponse(
                id=api_key.id,
                name=api_key.name,
                access_key=api_key.access_key,
                secret_key=raw_key,
                total_requests=api_key.total_requests,
                created_at=api_key.created_at,
            )

    async def get_by_hash(self, secret_hash: str) -> APIKeyModel | None:
        async with get_db() as db:
            result = await db.execute(select(APIKey).where(APIKey.secret_hash == secret_hash))
            api_key = result.scalar_one_or_none()
            return APIKeyModel.model_validate(api_key) if api_key else None

    async def get_list_by_user(self, user_id: int) -> list[APIKeyResponse]:
        async with get_db() as db:
            result = await db.execute(select(APIKey).where(APIKey.user_id == user_id))
            keys = result.scalars().all()
            return [APIKeyResponse.model_validate(k) for k in keys]

    async def update(self, key_id: int, user_id: int, form: APIKeyUpdate) -> APIKeyResponse | None:
        async with get_db() as db:
            result = await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id))
            api_key = result.scalar_one_or_none()

            if api_key is None:
                return None

            update_data = form.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(api_key, key, value)

            api_key.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(api_key)

            return APIKeyResponse.model_validate(api_key)

    async def update_usage(self, key_id: int):
        async with get_db() as db:
            result = await db.execute(select(APIKey).where(APIKey.id == key_id))
            api_key = result.scalar_one_or_none()

            if api_key:
                api_key.last_used_at = datetime.now(timezone.utc)
                api_key.total_requests += 1

                await db.commit()

    async def update_last_used(self, key_id: int):
        async with get_db() as db:
            result = await db.execute(select(APIKey).where(APIKey.id == key_id))
            api_key = result.scalar_one_or_none()
            if api_key:
                api_key.last_used_at = datetime.now(timezone.utc)
                await db.commit()

    async def delete(self, key_id: int, user_id: int) -> bool:
        async with get_db() as db:
            result = await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id))
            api_key = result.scalar_one_or_none()

            if api_key is None:
                return False

            await db.delete(api_key)
            await db.commit()
            return True


APIKeys = APIKeyTable()
