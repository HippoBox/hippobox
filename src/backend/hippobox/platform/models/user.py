from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import (
    JSON,
    event,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from hippobox.platform.core.db.session import Base, get_db
from hippobox.platform.core.error import AuthErrorCode, AuthException
from hippobox.platform.models.pagination import PageResponse
from hippobox.platform.models.profile_location import LOCATION_CODES

EMAIL_PATTERN = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"
    MANAGER = "manager"


class RoleChangeAudit(Base):
    """Operator receipt retained independently of account deletion; no email/token data."""

    __tablename__ = "role_change_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_role: Mapped[str] = mapped_column(String(20), nullable=False)
    new_role: Mapped[str] = mapped_column(String(20), nullable=False)
    operator: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class User(Base):
    __tablename__ = "user"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(SQLEnum(UserRole, name="userrole"), default=UserRole.USER, nullable=False)
    guide_seen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    profile_photo: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    keyboard_shortcuts: Mapped[dict[str, list[str]] | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    credential = relationship(
        "Credential", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    auth_identities = relationship(
        "AuthIdentity", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys = relationship("hippobox.platform.models.api_key.APIKey", back_populates="user", cascade="all, delete-orphan")


@event.listens_for(User, "before_insert")
def allocate_sqlite_user_id(mapper, connection, user):
    # Legacy SQLite tables lacked AUTOINCREMENT. Allocate from a persistent
    # high-water mark so an old JWT can never authenticate a reused user ID.
    if connection.dialect.name == "sqlite" and user.id is None:
        user.id = connection.execute(text(
            'UPDATE hippobox_user_sequence SET value = MAX(value, '
            '(SELECT COALESCE(MAX(id), 0) FROM "user")) + 1 WHERE id = 1 RETURNING value'
        )).scalar_one()


class Credential(Base):
    __tablename__ = "credential"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user = relationship("User", back_populates="credential")


class AuthIdentity(Base):
    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "identifier", name="uq_auth_identities_provider_identifier"),
        UniqueConstraint("user_id", "provider", name="uq_auth_identities_user_provider"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), default="email", nullable=False)
    identifier: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_login_user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user = relationship("User", back_populates="auth_identities")


class DeleteAccountCodeResponse(BaseModel):
    expires_in: int
    retry_after: int


class DeleteAccountForm(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    code: str = Field(pattern=r"^[0-9]{6}$")


class SignupForm(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    name: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=8, max_length=64)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(char.isupper() for char in value):
            raise ValueError("Password must include at least one uppercase letter.")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must include at least one number.")
        if not any(not char.isalnum() for char in value):
            raise ValueError("Password must include at least one symbol.")
        if any(char.isspace() for char in value):
            raise ValueError("Password cannot contain spaces.")
        return value


class LoginForm(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    password: str = Field(min_length=8, max_length=64)
    remember_me: bool = False


ShortcutKey = Annotated[str, Field(min_length=1, max_length=32)]
ShortcutKeys = Annotated[list[ShortcutKey], Field(min_length=1, max_length=5)]


class KeyboardShortcuts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    toggleSidebar: ShortcutKeys
    openSettings: ShortcutKeys
    openProfile: ShortcutKeys | None = None

    @model_validator(mode="after")
    def validate_bindings(self):
        modifiers = {"mod", "ctrl", "meta", "alt", "shift"}
        bindings = [self.toggleSidebar, self.openSettings]
        if self.openProfile is not None:
            bindings.append(self.openProfile)
        for keys in bindings:
            primary = [key for key in keys if key not in modifiers]
            if (
                len(primary) != 1
                or primary[0] in {"dead", "unidentified", "control"}
                or any(key != key.lower() or not key.isprintable() or key.isspace() for key in keys)
                or len(set(keys)) != len(keys)
            ):
                raise ValueError("Invalid shortcut keys.")
        for platform_modifier in ("meta", "ctrl"):
            resolved = [
                [platform_modifier if key == "mod" else key for key in keys] for keys in bindings
            ]
            if any(len(set(keys)) != len(keys) for keys in resolved):
                raise ValueError("Duplicate shortcut modifier.")
            if len({frozenset(keys) for keys in resolved}) != len(resolved):
                raise ValueError("Shortcut bindings must be distinct on every platform.")
        return self


class UpdateProfileForm(BaseModel):
    bio: str | None = Field(default=None, max_length=100)
    location: str | None = Field(
        default=None,
        max_length=100,
        description="Pinned country:region ID selected from the location catalog, or null.",
    )

    @field_validator("bio")
    @classmethod
    def normalize_profile_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    keyboard_shortcuts: KeyboardShortcuts | None = None
    name: str | None = Field(default=None, min_length=2, max_length=50)
    profile_image_url: str | None = Field(
        default=None,
        deprecated=True,
        description="Use PUT/DELETE /auth/me/photo; legacy PATCH photo writes are rejected.",
    )

    @field_validator("location")
    @classmethod
    def validate_location(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        if value not in LOCATION_CODES:
            raise ValueError("Select a supported country and region.")
        return value

    @field_validator("profile_image_url")
    @classmethod
    def validate_profile_image_url(cls, value: str | None) -> str | None:
        raise ValueError("Use PUT/DELETE /auth/me/photo to change the profile photo.")

    @model_validator(mode="after")
    def validate_fields(self):
        has_name = "name" in self.model_fields_set
        has_profile_image_url = "profile_image_url" in self.model_fields_set
        if (
            not has_name
            and not has_profile_image_url
            and "keyboard_shortcuts" not in self.model_fields_set
            and "bio" not in self.model_fields_set
            and "location" not in self.model_fields_set
        ):
            raise ValueError("At least one field must be provided.")
        if has_name and self.name is None:
            raise ValueError("name cannot be null.")
        return self


class UserResponse(BaseModel):
    guide_seen: bool = False
    bio: str | None = None
    location: str | None = None
    has_password: bool = False
    id: int
    email: str
    name: str
    role: UserRole
    profile_image_url: str | None = None
    keyboard_shortcuts: KeyboardShortcuts | None = None
    oauth_providers: list[str] = Field(default_factory=list)
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRoleStatsResponse(BaseModel):
    total_users: int
    active_users: int
    admin_users: int
    manager_users: int = 0


class AdminUserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: datetime | None
    login_providers: list[str]


class AdminUserListResponse(PageResponse[AdminUserResponse]):
    summary: UserRoleStatsResponse


class VerifyEmailForm(BaseModel):
    token: str = Field(min_length=16, max_length=512)


class VerifyEmailResponse(BaseModel):
    message: str
    user: UserResponse


class ResendVerificationForm(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)


class ResendVerificationResponse(BaseModel):
    message: str


class ForgotPasswordForm(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordForm(BaseModel):
    token: str = Field(min_length=16, max_length=512)
    password: str = Field(min_length=8, max_length=64)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(char.isupper() for char in value):
            raise ValueError("Password must include at least one uppercase letter.")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must include at least one number.")
        if not any(not char.isalnum() for char in value):
            raise ValueError("Password must include at least one symbol.")
        if any(char.isspace() for char in value):
            raise ValueError("Password cannot contain spaces.")
        return value


class VerifyAccountCodeForm(BaseModel):
    code: str = Field(pattern=r"^[0-9]{6}$")


class ChangePasswordForm(BaseModel):
    code: str = Field(pattern=r"^[0-9]{6}$")
    password: str = Field(min_length=8, max_length=64)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        return ResetPasswordForm.validate_password_strength(value)


class ResetPasswordResponse(BaseModel):
    message: str


class APIError(BaseModel):
    error: str
    message: str
    details: dict | None = None


class AuthUserDTO(BaseModel):
    guide_seen: bool = False
    bio: str | None = None
    location: str | None = None
    id: int
    email: str
    name: str
    role: UserRole
    profile_image_url: str | None = None
    keyboard_shortcuts: KeyboardShortcuts | None = None
    oauth_providers: list[str] = Field(default_factory=list)
    is_active: bool
    is_verified: bool
    created_at: datetime
    password_hash: str | None = None

    def as_user_response(self) -> UserResponse:
        return UserResponse(
            guide_seen=self.guide_seen,
            id=self.id,
            email=self.email,
            name=self.name,
            role=self.role,
            profile_image_url=self.profile_image_url,
            keyboard_shortcuts=self.keyboard_shortcuts,
            bio=self.bio,
            location=self.location,
            has_password=bool(self.password_hash),
            oauth_providers=self.oauth_providers,
            is_verified=self.is_verified,
            created_at=self.created_at,
        )


def _extract_connected_oauth_providers(auth_identities: list[AuthIdentity] | None) -> list[str]:
    if not auth_identities:
        return []

    connected = {
        identity.provider.strip().lower()
        for identity in auth_identities
        if identity.provider and identity.provider.strip().lower() != "email"
    }
    return sorted(connected)


class UserRepository:
    async def create_signup_user(
        self,
        email: str,
        name: str,
        password_hash: str,
        is_verified: bool = False,
        role: UserRole = UserRole.USER,
    ) -> UserResponse:
        async with get_db() as db:
            existing = await db.execute(select(User.id).where(User.email == email).limit(1))
            if existing.first() is not None:
                raise AuthException(code=AuthErrorCode.EMAIL_ALREADY_EXISTS)

            existing_name = await db.execute(select(User.id).where(User.name == name).limit(1))
            if existing_name.first() is not None:
                raise AuthException(code=AuthErrorCode.NAME_ALREADY_EXISTS)

            user = User(email=email, name=name, role=role.value, is_verified=is_verified)
            user.credential = Credential(password_hash=password_hash)
            user.auth_identities = [AuthIdentity(provider="email", identifier=email)]
            db.add(user)

            try:
                await db.flush()
                from hippobox.platform.models.inbox import add_inbox_notification

                await add_inbox_notification(
                    db,
                    user_id=user.id,
                    kind="welcome",
                    title="Welcome to HippoBox",
                    body="Your account is ready. Welcome to HippoBox.",
                    action_path="/app",
                )
                await db.commit()
                await db.refresh(user)
            except IntegrityError:
                await db.rollback()
                raise

            return UserResponse.model_validate(user)

    async def create_oauth_user(
        self,
        email: str,
        name: str,
        provider: str,
        identifier: str,
        is_verified: bool = True,
        role: UserRole = UserRole.USER,
    ) -> UserResponse:
        async with get_db() as db:
            existing = await db.execute(select(User.id).where(User.email == email).limit(1))
            if existing.first() is not None:
                raise AuthException(code=AuthErrorCode.EMAIL_ALREADY_EXISTS)

            existing_name = await db.execute(select(User.id).where(User.name == name).limit(1))
            if existing_name.first() is not None:
                raise AuthException(code=AuthErrorCode.NAME_ALREADY_EXISTS)

            user = User(email=email, name=name, role=role.value, is_verified=is_verified)
            user.auth_identities = [AuthIdentity(provider=provider, identifier=identifier)]
            db.add(user)

            try:
                await db.flush()
                from hippobox.platform.models.inbox import add_inbox_notification

                await add_inbox_notification(
                    db,
                    user_id=user.id,
                    kind="welcome",
                    title="Welcome to HippoBox",
                    body="Your account is ready. Welcome to HippoBox.",
                    action_path="/app",
                )
                await db.commit()
                await db.refresh(user)
            except IntegrityError:
                await db.rollback()
                raise

            return UserResponse.model_validate(user)

    async def get_auth_user_by_identity(self, provider: str, identifier: str) -> AuthUserDTO | None:
        async with get_db() as db:
            result = await db.execute(
                select(User)
                .join(AuthIdentity, AuthIdentity.user_id == User.id)
                .options(selectinload(User.credential), selectinload(User.auth_identities))
                .where(
                    AuthIdentity.provider == provider,
                    AuthIdentity.identifier == identifier,
                    User.is_active.is_(True),
                )
            )
            user = result.scalar_one_or_none()

        if user is None:
            return None

        return AuthUserDTO(
            guide_seen=user.guide_seen,
            id=user.id,
            email=user.email,
            name=user.name,
            role=UserRole(user.role),
            profile_image_url=user.profile_image_url,
            keyboard_shortcuts=user.keyboard_shortcuts,
            bio=user.bio,
            location=user.location,
            oauth_providers=_extract_connected_oauth_providers(user.auth_identities),
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            password_hash=user.credential.password_hash if user.credential and user.credential.is_active else None,
        )

    async def has_bootstrap_identity(self, user_id: int) -> bool:
        async with get_db() as db:
            identity_id = await db.scalar(
                select(AuthIdentity.id)
                .where(AuthIdentity.user_id == user_id, AuthIdentity.provider == "bootstrap")
                .limit(1)
            )
            return identity_id is not None

    async def get_auth_user_by_email(self, email: str) -> AuthUserDTO | None:
        return await self.get_auth_user_by_identity(provider="email", identifier=email)

    async def get_user_response_by_email(self, email: str) -> UserResponse | None:
        async with get_db() as db:
            result = await db.execute(
                select(User).where(User.email == email, User.is_active.is_(True))
            )
            user = result.scalar_one_or_none()
            if user is None:
                return None
            return UserResponse.model_validate(user)

    async def get_auth_user_by_id(self, user_id: int) -> AuthUserDTO | None:
        async with get_db() as db:
            result = await db.execute(
                select(User)
                .options(selectinload(User.credential), selectinload(User.auth_identities))
                .where(User.id == user_id, User.is_active.is_(True))
            )
            user = result.scalar_one_or_none()

        if user is None:
            return None

        return AuthUserDTO(
            guide_seen=user.guide_seen,
            id=user.id,
            email=user.email,
            name=user.name,
            role=UserRole(user.role),
            profile_image_url=user.profile_image_url,
            keyboard_shortcuts=user.keyboard_shortcuts,
            bio=user.bio,
            location=user.location,
            oauth_providers=_extract_connected_oauth_providers(user.auth_identities),
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            password_hash=user.credential.password_hash if user.credential and user.credential.is_active else None,
        )

    async def get_user_response_by_id(self, user_id: int) -> UserResponse | None:
        auth_user = await self.get_auth_user_by_id(user_id)
        if auth_user is None:
            return None
        return auth_user.as_user_response()

    async def link_auth_identity(self, user_id: int, provider: str, identifier: str) -> bool:
        async with get_db() as db:
            auth_identity = AuthIdentity(
                user_id=user_id,
                provider=provider,
                identifier=identifier,
            )
            db.add(auth_identity)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                return False
        return True

    async def update_login_metadata(
        self,
        user_id: int,
        provider: str,
        identifier: str,
        login_ip: str | None,
        user_agent: str | None,
        login_time: datetime,
    ) -> None:
        async with get_db() as db:
            result = await db.execute(
                select(AuthIdentity).where(
                    AuthIdentity.user_id == user_id,
                    AuthIdentity.provider == provider,
                    AuthIdentity.identifier == identifier,
                )
            )
            auth_identity = result.scalar_one_or_none()
            if auth_identity is None:
                return

            auth_identity.last_login_at = login_time
            auth_identity.last_login_ip = login_ip
            auth_identity.last_login_user_agent = user_agent
            await db.commit()

    async def mark_email_verified(self, user_id: int) -> UserResponse | None:
        async with get_db() as db:
            result = await db.execute(
                update(User)
                .where(User.id == user_id, User.is_active.is_(True), User.is_verified.is_(False))
                .values(is_verified=True)
                .returning(User)
            )
            user = result.scalar_one_or_none()
            await db.commit()
            return UserResponse.model_validate(user) if user else None

    async def update_password_hash(self, user_id: int, password_hash: str) -> bool:
        async with get_db() as db:
            result = await db.execute(
                select(Credential)
                .join(User, User.id == Credential.user_id)
                .where(User.id == user_id, User.is_active.is_(True))
            )
            credential = result.scalar_one_or_none()
            if credential is None:
                return False

            credential.password_hash = password_hash
            credential.updated_at = datetime.now(UTC)
            await db.commit()
            return True

    async def change_password_hash(
        self, user_id: int, previous_hash: str, password_hash: str
    ) -> bool:
        async with get_db() as db:
            result = await db.execute(
                update(Credential)
                .where(
                    Credential.user_id == user_id,
                    Credential.password_hash == previous_hash,
                    Credential.user_id.in_(select(User.id).where(User.is_active.is_(True))),
                )
                .values(password_hash=password_hash, updated_at=datetime.now(UTC))
            )
            await db.commit()
            return result.rowcount == 1

    async def update_user_profile(
        self,
        user_id: int,
        *,
        name: str | None,
        profile_image_url: str | None,
        update_name: bool,
        update_profile_image_url: bool,
        keyboard_shortcuts: KeyboardShortcuts | None = None,
        update_keyboard_shortcuts: bool = False,
        bio: str | None = None,
        location: str | None = None,
        update_bio: bool = False,
        update_location: bool = False,
    ) -> UserResponse | None:
        async with get_db() as db:
            result = await db.execute(
                select(User).where(User.id == user_id, User.is_active.is_(True))
            )
            user = result.scalar_one_or_none()
            if user is None:
                return None

            if update_bio:
                user.bio = bio
            if update_location:
                user.location = location
            if update_name and name is not None:
                user.name = name
            if update_profile_image_url:
                user.profile_image_url = profile_image_url
            if update_keyboard_shortcuts:
                user.keyboard_shortcuts = (
                    keyboard_shortcuts.model_dump() if keyboard_shortcuts else None
                )
            user.updated_at = datetime.now(UTC)
            await db.commit()
        return await self.get_user_response_by_id(user_id)

    async def update_user_role(self, user_id: int, role: UserRole) -> UserResponse | None:
        user = await self.get_user_response_by_id(user_id)
        if user is None:
            return None
        await self.set_operator_role(user.email, role, operator="internal")
        return await self.get_user_response_by_id(user_id)

    async def delete_account(self, user_id: int, email: str, notification=None) -> dict | None:
        """Delete credentials and owned keys atomically; serialize with role changes."""
        from hippobox.platform.models.billing import BillingCheckout

        async with get_db() as db:
            if db.bind.dialect.name == "sqlite":
                await db.execute(text("BEGIN IMMEDIATE"))
            elif db.bind.dialect.name == "postgresql":
                await db.execute(text('LOCK TABLE "user" IN SHARE ROW EXCLUSIVE MODE'))
            user = await db.scalar(select(User).where(User.id == user_id).with_for_update())
            if user is None or not user.is_active:
                raise AuthException(code=AuthErrorCode.USER_NOT_FOUND)
            if user.email.casefold() != email.strip().casefold():
                raise AuthException(code=AuthErrorCode.ACCOUNT_DELETE_CONFIRMATION_REQUIRED)
            if user.role == UserRole.ADMIN.value:
                admins = await db.scalar(
                    select(func.count(User.id)).where(
                        User.role == UserRole.ADMIN.value, User.is_active.is_(True)
                    )
                )
                if admins <= 1:
                    raise AuthException(code=AuthErrorCode.LAST_ADMIN_REQUIRED)
            if (
                await db.scalar(
                    select(BillingCheckout.user_id)
                    .where(BillingCheckout.user_id == user_id)
                    .limit(1)
                )
                is not None
            ):
                raise AuthException(code=AuthErrorCode.ACCOUNT_BILLING_REVIEW_REQUIRED)
            if notification is not None:
                db.add(notification)
            photo = user.profile_photo
            await db.delete(user)
            await db.commit()
            return photo

    async def set_operator_role(
        self, email: str, role: UserRole, *, operator: str = "operator"
    ) -> tuple[int, str, str]:
        """Serialize operator changes and preserve at least one existing active admin."""
        async with get_db() as db:
            dialect = db.bind.dialect.name
            if dialect == "sqlite":
                await db.execute(text("BEGIN IMMEDIATE"))
            elif dialect == "postgresql":
                await db.execute(text('LOCK TABLE "user" IN SHARE ROW EXCLUSIVE MODE'))
            else:
                raise ValueError("Role management supports SQLite and PostgreSQL only.")
            user = await db.scalar(select(User).where(User.email == email))
            if user is None or not user.is_active:
                raise ValueError(
                    "Active user not found; create the account before assigning a role."
                )
            previous = user.role
            if previous == UserRole.ADMIN.value and role != UserRole.ADMIN:
                admins = await db.scalar(
                    select(func.count(User.id)).where(
                        User.role == UserRole.ADMIN.value, User.is_active.is_(True)
                    )
                )
                if admins <= 1:
                    raise ValueError(
                        "Cannot demote the last active admin; promote another user first."
                    )
            if previous != role.value:
                db.add(
                    RoleChangeAudit(
                        target_user_id=user.id,
                        previous_role=previous,
                        new_role=role.value,
                        operator=operator,
                    )
                )
            user.role = role.value
            user.updated_at = datetime.now(UTC)
            await db.commit()
            return user.id, previous, role.value

    async def list_demo_user_projection(self) -> list[dict]:
        """Exclude names, emails, profile and credentials at the database boundary."""
        async with get_db() as db:
            result = await db.execute(
                select(
                    User.id, User.role, User.is_active, User.is_verified, User.created_at
                ).order_by(User.id.desc())
            )
            users = [dict(row) for row in result.mappings()]
            identities = await db.execute(
                select(AuthIdentity.user_id, AuthIdentity.provider, AuthIdentity.last_login_at)
            )
            by_user: dict[int, list] = {}
            for identity in identities:
                by_user.setdefault(identity.user_id, []).append(identity)
            for user in users:
                linked = by_user.get(user["id"], [])
                user["login_providers"] = sorted({item.provider for item in linked})
                dates = [item.last_login_at for item in linked if item.last_login_at]
                user["last_login_at"] = max(dates) if dates else None
            return users

    async def list_admin_users(
        self,
        *,
        page: int,
        page_size: int,
        search: str,
        role: UserRole | None,
        is_active: bool | None,
    ) -> AdminUserListResponse:
        filters = []
        if search:
            filters.append(
                or_(
                    User.email.icontains(search, autoescape=True),
                    User.name.icontains(search, autoescape=True),
                )
            )
        if role is not None:
            filters.append(User.role == role.value)
        if is_active is not None:
            filters.append(User.is_active.is_(is_active))
        last_login = (
            select(
                AuthIdentity.user_id, func.max(AuthIdentity.last_login_at).label("last_login_at")
            )
            .group_by(AuthIdentity.user_id)
            .subquery()
        )
        async with get_db() as db:
            total = await db.scalar(select(func.count(User.id)).where(*filters))
            result = await db.execute(
                select(User, last_login.c.last_login_at)
                .outerjoin(last_login, User.id == last_login.c.user_id)
                .options(selectinload(User.auth_identities))
                .where(*filters)
                .order_by(User.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            items = [
                AdminUserResponse(
                    id=user.id,
                    email=user.email,
                    name=user.name,
                    role=UserRole(user.role),
                    is_active=user.is_active,
                    is_verified=user.is_verified,
                    created_at=user.created_at.replace(tzinfo=UTC)
                    if user.created_at.tzinfo is None
                    else user.created_at,
                    last_login_at=(
                        last_login_at.replace(tzinfo=UTC)
                        if last_login_at is not None and last_login_at.tzinfo is None
                        else last_login_at
                    ),
                    login_providers=sorted(identity.provider for identity in user.auth_identities),
                )
                for user, last_login_at in result.all()
            ]
        return AdminUserListResponse(
            items=items,
            total=total or 0,
            page=page,
            page_size=page_size,
            summary=UserRoleStatsResponse(**await self.get_user_role_stats()),
        )

    async def get_user_role_stats(self) -> dict[str, int]:
        async with get_db() as db:
            total_users = await db.scalar(select(func.count(User.id)))
            active_users = await db.scalar(
                select(func.count(User.id)).where(User.is_active.is_(True))
            )
            manager_users = await db.scalar(
                select(func.count(User.id)).where(User.role == UserRole.MANAGER.value)
            )
            admin_users = await db.scalar(
                select(func.count(User.id)).where(User.role == UserRole.ADMIN.value)
            )

        return {
            "total_users": int(total_users or 0),
            "active_users": int(active_users or 0),
            "admin_users": int(admin_users or 0),
            "manager_users": int(manager_users or 0),
        }


Users = UserRepository()
