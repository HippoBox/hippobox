"""Durable OAuth state, independent of Redis and of application login tokens."""

import hashlib
import time

from sqlalchemy import JSON, Boolean, Integer, String, delete, update
from sqlalchemy.orm import Mapped, mapped_column

from hippobox.core.database import Base, get_db


class OAuthRecord(Base):
    __tablename__ = "mcp_oauth_record"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    data: Mapped[dict] = mapped_column(JSON)
    expires: Mapped[int] = mapped_column(Integer, index=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    family: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def record(key: str, kind: str, data: dict, lifetime: int, family: str | None = None):
    return OAuthRecord(key=digest(key), kind=kind, data=data, expires=int(time.time()) + lifetime, family=family)


async def save(value: OAuthRecord):
    async with get_db() as db:
        await db.execute(delete(OAuthRecord).where(OAuthRecord.expires < int(time.time())))
        db.add(value)
        await db.commit()


async def load(key: str, kind: str) -> OAuthRecord | None:
    async with get_db() as db:
        value = await db.get(OAuthRecord, digest(key))
        if value and value.kind == kind and value.expires > time.time():
            return value
    return None


async def consume(db, key: str) -> bool:
    result = await db.execute(
        update(OAuthRecord)
        .where(OAuthRecord.key == digest(key), OAuthRecord.used.is_(False), OAuthRecord.expires > int(time.time()))
        .values(used=True)
    )
    return result.rowcount == 1


async def revoke_family(db, family: str):
    await db.execute(update(OAuthRecord).where(OAuthRecord.family == family).values(used=True))
