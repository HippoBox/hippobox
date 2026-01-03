import logging
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column

from hippobox.core.database import Base, get_db

log = logging.getLogger("auth")


class Auth(Base):
    __tablename__ = "auth"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(nullable=False, default="email")
    identifier: Mapped[str] = mapped_column(nullable=False, index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(nullable=True)
    last_login_user_agent: Mapped[str | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class AuthModel(BaseModel):
    id: int = Field(..., description="Unique identifier of the auth entry")

    user_id: int = Field(..., description="User identifier tied to this auth record")
    provider: str = Field(..., description="Authentication provider (e.g., email, google)")
    identifier: str = Field(..., description="Provider-specific identifier (e.g., email address)")
    last_login_at: datetime | None = Field(None, description="Timestamp of the most recent successful login")
    last_login_ip: str | None = Field(None, description="IP address from the most recent successful login")
    last_login_user_agent: str | None = Field(None, description="User agent from the most recent successful login")

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class AuthTable:
    async def create(self, user_id: int, provider: str, identifier: str) -> AuthModel:
        async with get_db() as db:
            auth = Auth(
                user_id=user_id,
                provider=provider,
                identifier=identifier,
                last_login_at=None,
                last_login_ip=None,
                last_login_user_agent=None,
            )
            db.add(auth)
            await db.commit()
            await db.refresh(auth)
            return AuthModel.model_validate(auth)

    async def get_by_user_id(self, user_id: int) -> AuthModel | None:
        async with get_db() as db:
            result = await db.execute(select(Auth).where(Auth.user_id == user_id))
            auth = result.scalar_one_or_none()
            return AuthModel.model_validate(auth) if auth else None

    async def update_last_login(
        self,
        user_id: int,
        login_time: datetime,
        login_ip: str | None,
        user_agent: str | None,
    ) -> AuthModel | None:
        async with get_db() as db:
            result = await db.execute(select(Auth).where(Auth.user_id == user_id))
            auth = result.scalar_one_or_none()

            if auth is None:
                return None

            auth.last_login_at = login_time
            auth.last_login_ip = login_ip
            auth.last_login_user_agent = user_agent
            auth.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(auth)
            return AuthModel.model_validate(auth)


Auths = AuthTable()
