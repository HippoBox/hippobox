import logging
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import select

from hippobox.core.database import get_db
from hippobox.platform.models.user import Credential as Credential

log = logging.getLogger("credential")


class CredentialModel(BaseModel):
    id: int = Field(..., description="Unique identifier of the credential entry")

    user_id: int = Field(..., description="User identifier tied to this credential")
    password_hash: str = Field(..., description="Hashed password value")
    is_active: bool = Field(..., description="Whether the credential is active")
    password_changed_at: datetime | None = Field(None, description="Timestamp when the password was last changed")

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class CredentialTable:
    async def create(self, user_id: int, password_hash: str) -> CredentialModel:
        async with get_db() as db:
            credential = Credential(
                user_id=user_id,
                password_hash=password_hash,
                is_active=True,
                password_changed_at=datetime.now(timezone.utc),
            )
            db.add(credential)
            await db.commit()
            await db.refresh(credential)
            return CredentialModel.model_validate(credential)

    async def get_by_user_id(self, user_id: int) -> CredentialModel | None:
        async with get_db() as db:
            result = await db.execute(select(Credential).where(Credential.user_id == user_id))
            credential = result.scalar_one_or_none()
            return CredentialModel.model_validate(credential) if credential else None

    async def update(self, user_id: int, form: dict) -> CredentialModel | None:
        async with get_db() as db:
            result = await db.execute(select(Credential).where(Credential.user_id == user_id))
            credential = result.scalar_one_or_none()

            if credential is None:
                return None

            for key, value in form.items():
                if hasattr(credential, key):
                    setattr(credential, key, value)

            credential.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(credential)
            return CredentialModel.model_validate(credential)


Credentials = CredentialTable()
