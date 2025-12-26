import logging
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from hippobox.core.database import Base, get_db
from hippobox.errors.auth import AuthErrorCode, AuthException

log = logging.getLogger("user")


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(default=UserRole.USER, nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class UserModel(BaseModel):
    id: int = Field(..., description="Unique identifier of the user entry")

    email: str = Field(..., description="User's unique email address, used for authentication and identification")
    name: str = Field(..., description="Display name of the user")
    role: UserRole = Field(..., description="Role assigned to the user")

    is_active: bool = Field(..., description="Indicates whether the user account is active")
    is_verified: bool = Field(..., description="Indicates whether the user's email has been verified successfully")

    created_at: datetime = Field(..., description="Timestamp indicating when the user account was created")
    updated_at: datetime = Field(..., description="Timestamp indicating the most recent update to the user record")

    class Config:
        from_attributes = True


class SignupForm(BaseModel):
    email: str = Field(..., description="Email address used to register the new user")
    password: str = Field(..., description="Raw password that will be hashed and stored securely")
    name: str = Field(..., description="Display name assigned to the new user")


class LoginForm(BaseModel):
    email: str = Field(..., description="Email used for login")
    password: str = Field(..., description="Raw password for login")


class UserResponse(BaseModel):
    id: int = Field(..., description="Unique identifier of the user")
    email: str = Field(..., description="User's registered email address")
    name: str = Field(..., description="Display name of the user")
    role: UserRole = Field(..., description="Role assigned to the user")
    created_at: datetime = Field(..., description="Timestamp when the user account was created")

    class Config:
        from_attributes = True


class LoginTokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token used for authentication")
    refresh_token: str = Field(..., description="Refresh token used to renew access tokens")
    token_type: str = Field("bearer", description="Type of the token (e.g., 'bearer')")
    user: UserResponse = Field(..., description="Authenticated user information associated with the token")


class TokenRefreshResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token used for authentication")
    refresh_token: str = Field(..., description="Refresh token used to renew access tokens")
    token_type: str = Field("bearer", description="Type of the token (e.g., 'bearer')")


class UserTable:
    async def create(self, form: dict) -> UserModel:
        async with get_db() as db:
            try:
                user = User(
                    email=form["email"],
                    name=form["name"],
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                return UserModel.model_validate(user)

            except IntegrityError as e:
                await db.rollback()
                msg = str(e.orig)

                if "user_email_key" in msg:
                    raise AuthException(AuthErrorCode.EMAIL_ALREADY_EXISTS)

                if "user_name_key" in msg:
                    raise AuthException(AuthErrorCode.NAME_ALREADY_EXISTS)

                raise AuthException(AuthErrorCode.CREATE_FAILED, str(e))

    async def get(self, user_id: int) -> UserModel | None:
        async with get_db() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            return UserModel.model_validate(user) if user else None

    async def get_by_email(self, email: str) -> UserModel | None:
        async with get_db() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            return UserModel.model_validate(user) if user else None

    # Used only in the service layer (never expose raw ORM entities to routers)
    async def get_entity_by_email(self, email: str) -> User | None:
        async with get_db() as db:
            result = await db.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()

    async def get_list(self) -> list[UserModel]:
        async with get_db() as db:
            result = await db.execute(select(User))
            users = result.scalars().all()
            return [UserModel.model_validate(u) for u in users]

    async def update(self, user_id: int, form: dict) -> UserModel | None:
        async with get_db() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if user is None:
                return None

            for key, value in form.items():
                if hasattr(user, key):
                    setattr(user, key, value)

            user.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(user)
            return UserModel.model_validate(user)

    async def delete(self, user_id: int) -> bool:
        async with get_db() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user is None:
                return False

            await db.delete(user)
            await db.commit()
            return True


Users = UserTable()
