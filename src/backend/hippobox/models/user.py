import logging
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from hippobox.core.database import get_db
from hippobox.core.validation import (
    EMAIL_REGEX,
    NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
    NAME_REGEX,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    PASSWORD_REGEX,
    is_password_strong,
)
from hippobox.errors.auth import AuthErrorCode, AuthException, user_integrity_exception
from hippobox.models.auth import Auth
from hippobox.models.credential import Credential
from hippobox.platform.models.user import User, UserRole

log = logging.getLogger("user")


class UserModel(BaseModel):
    id: int = Field(..., description="Unique identifier of the user entry")

    email: str = Field(..., description="User's unique email address, used for authentication and identification")
    name: str = Field(..., description="Display name of the user")
    role: UserRole = Field(..., description="Role assigned to the user")

    is_active: bool = Field(..., description="Indicates whether the user account is active")
    is_verified: bool = Field(..., description="Indicates whether the user's email has been verified successfully")
    guide_seen: bool = Field(False, description="Whether the onboarding guide has been seen")

    created_at: datetime = Field(..., description="Timestamp indicating when the user account was created")
    updated_at: datetime = Field(..., description="Timestamp indicating the most recent update to the user record")

    class Config:
        from_attributes = True


class SignupForm(BaseModel):
    email: str = Field(
        ...,
        description="Email address used to register the new user",
        pattern=EMAIL_REGEX,
    )
    password: str = Field(
        ...,
        description="Raw password that will be hashed (8-64 chars, uppercase+digit+symbol, no spaces)",
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        pattern=PASSWORD_REGEX,
    )
    name: str = Field(
        ...,
        description="Display name assigned to the new user",
        min_length=NAME_MIN_LENGTH,
        max_length=NAME_MAX_LENGTH,
        pattern=NAME_REGEX,
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not is_password_strong(value):
            raise ValueError(
                "Password must be 8-64 characters and include an uppercase letter, a number, and a symbol."
            )
        return value


class LoginForm(BaseModel):
    email: str = Field(
        ...,
        description="Email used for login",
        pattern=EMAIL_REGEX,
    )
    password: str = Field(
        ...,
        description="Raw password for login (8-64 chars, uppercase+digit+symbol, no spaces)",
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        pattern=PASSWORD_REGEX,
    )
    remember_me: bool = Field(
        False,
        description="If true, issue a persistent refresh cookie for login persistence",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not is_password_strong(value):
            raise ValueError(
                "Password must be 8-64 characters and include an uppercase letter, a number, and a symbol."
            )
        return value


class PasswordResetRequest(BaseModel):
    email: str = Field(
        ...,
        description="Email address used to request a password reset",
        pattern=EMAIL_REGEX,
    )


class EmailVerificationResend(BaseModel):
    email: str = Field(
        ...,
        description="Email address used to resend a verification link",
        pattern=EMAIL_REGEX,
    )


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., description="Valid password reset token")
    new_password: str = Field(
        ...,
        description="New password to set (8-64 chars, uppercase+digit+symbol, no spaces)",
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        pattern=PASSWORD_REGEX,
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if not is_password_strong(value):
            raise ValueError(
                "Password must be 8-64 characters and include an uppercase letter, a number, and a symbol."
            )
        return value


class UserResponse(BaseModel):
    id: int = Field(..., description="Unique identifier of the user")
    email: str = Field(..., description="User's registered email address")
    name: str = Field(..., description="Display name of the user")
    role: UserRole = Field(..., description="Role assigned to the user")
    created_at: datetime = Field(..., description="Timestamp when the user account was created")
    guide_seen: bool = Field(False, description="Whether the onboarding guide has been seen")

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


class ProfileUpdateForm(BaseModel):
    name: str = Field(
        ...,
        description="Updated display name for the user",
        min_length=NAME_MIN_LENGTH,
        max_length=NAME_MAX_LENGTH,
        pattern=NAME_REGEX,
    )


class GuideSeenUpdateForm(BaseModel):
    seen: bool = Field(
        True,
        description="Whether the onboarding guide has been seen",
    )


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
                raise user_integrity_exception(e) from e

    async def create_with_role(self, form: dict, role: UserRole, is_verified: bool = False) -> UserModel:
        async with get_db() as db:
            try:
                user = User(
                    email=form["email"],
                    name=form["name"],
                    role=role,
                    is_verified=is_verified,
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                return UserModel.model_validate(user)

            except IntegrityError as e:
                await db.rollback()
                raise user_integrity_exception(e) from e

    async def create_signup_user(
        self, *, email: str, name: str, password_hash: str, is_verified: bool = False
    ) -> UserModel:
        """Persist all signup records atomically, following Blueprint's repository boundary."""
        async with get_db() as db:
            async with db.begin():
                for field, value, code in (
                    (User.email, email, AuthErrorCode.EMAIL_ALREADY_EXISTS),
                    (User.name, name, AuthErrorCode.NAME_ALREADY_EXISTS),
                ):
                    existing = await db.execute(select(User.id).where(field == value).limit(1))
                    if existing.first() is not None:
                        raise AuthException(code)
                user = User(email=email, name=name, role=UserRole.USER, is_verified=is_verified)
                db.add(user)
                await db.flush()
                db.add_all(
                    [
                        Credential(
                            user_id=user.id,
                            password_hash=password_hash,
                            password_changed_at=datetime.now(timezone.utc),
                        ),
                        Auth(user_id=user.id, provider="email", identifier=user.email),
                    ]
                )
                await db.flush()
                result = UserModel.model_validate(user)
            return result

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

    async def admin_exists(self) -> bool:
        async with get_db() as db:
            result = await db.execute(select(User.id).where(User.role == UserRole.ADMIN).limit(1))
            return result.first() is not None

    async def get_admin(self) -> UserModel | None:
        async with get_db() as db:
            result = await db.execute(select(User).where(User.role == UserRole.ADMIN).limit(1))
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

    async def update_profile(self, user_id: int, name: str) -> UserModel | None:
        async with get_db() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if user is None:
                return None

            user.name = name
            user.updated_at = datetime.now(timezone.utc)

            try:
                await db.commit()
            except IntegrityError as e:
                await db.rollback()
                raise user_integrity_exception(e) from e

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
