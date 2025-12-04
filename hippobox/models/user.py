import logging
from datetime import datetime, timezone

from passlib.hash import bcrypt
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column

from hippobox.core.database import Base, get_db

log = logging.getLogger("user")


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))


class UserModel(BaseModel):
    id: int = Field(..., description="Unique identifier of the user entry")
    email: str = Field(..., description="User's unique email address, used for authentication and identification")
    name: str = Field(..., description="Display name of the user")

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


class UserUpdate(BaseModel):
    email: str | None = Field(None, description="Updated email address, if the user wishes to change it")
    password: str | None = Field(
        None, description="New raw password to replace the existing one, hashed before storage"
    )
    name: str | None = Field(None, description="Updated display name for the user")


class UserResponse(BaseModel):
    id: int = Field(..., description="Unique identifier of the user")
    email: str = Field(..., description="User's registered email address")
    name: str = Field(..., description="Display name of the user")
    created_at: datetime = Field(..., description="Timestamp when the user account was created")


class UserTable:
    async def create(self, form: SignupForm) -> UserModel:
        async with get_db() as db:
            user = User(
                email=form.email,
                name=form.name,
                password_hash=bcrypt.hash(form.password),
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return UserModel.model_validate(user)

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

    async def update(self, user_id: int, form: UserUpdate) -> UserModel | None:
        async with get_db() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if user is None:
                return None

            update_data = form.model_dump(exclude_unset=True)
            if "password" in update_data:
                update_data["password_hash"] = bcrypt.hash(update_data.pop("password"))

            for key, value in update_data.items():
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
