"""Durable user-facing notifications, separate from the mail delivery outbox."""

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, PositiveInt
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from hippobox.platform.core.db.session import Base, get_db
from hippobox.platform.models.pagination import PageResponse


class InboxNotification(Base):
    __tablename__ = "inbox_notifications"
    __table_args__ = (
        Index("ix_inbox_owner_id", "user_id", "id"),
        Index("ix_inbox_delivery_key", "delivery_key", unique=True),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    delivery_key: Mapped[str | None] = mapped_column(String(64))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    action_path: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InboxItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    title: str
    body: str
    action_path: str | None
    created_at: datetime
    read_at: datetime | None


class InboxSummary(BaseModel):
    unread_count: int
    latest_id: int


class InboxPage(PageResponse[InboxItem]):
    summary: InboxSummary


class InboxSelectionForm(BaseModel):
    notification_ids: list[PositiveInt] = Field(min_length=1, max_length=100)


class InboxReadAllForm(BaseModel):
    through_id: int = Field(ge=0)


async def add_inbox_notification(
    db: AsyncSession,
    *,
    user_id: int,
    kind: str,
    title: str,
    body: str,
    action_path: str | None = None,
) -> None:
    """Domain producer owns commit; never store credentials or untrusted external links."""
    if action_path and (not action_path.startswith("/") or action_path.startswith("//")):
        raise ValueError("Inbox actions must be application-relative paths.")
    db.add(
        InboxNotification(
            user_id=user_id, kind=kind, title=title[:160], body=body[:2000], action_path=action_path
        )
    )


class InboxRepository:
    async def deliver(
        self, *, key: str, user_id: int, kind: str, title: str, body: str, action_path: str
    ) -> bool:
        digest = hashlib.sha256(f"{user_id}:{key}".encode()).hexdigest()
        async with get_db() as db:
            db.add(
                InboxNotification(
                    delivery_key=digest,
                    user_id=user_id,
                    kind=kind,
                    title=title,
                    body=body,
                    action_path=action_path,
                )
            )
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                if await db.scalar(
                    select(InboxNotification.id).where(InboxNotification.delivery_key == digest)
                ):
                    return False
                raise
        return True

    async def summary(self, user_id: int) -> InboxSummary:
        async with get_db() as db:
            unread = await db.scalar(
                select(func.count())
                .select_from(InboxNotification)
                .where(
                    InboxNotification.user_id == user_id,
                    InboxNotification.deleted_at.is_(None),
                    InboxNotification.read_at.is_(None),
                )
            )
            latest = await db.scalar(
                select(func.max(InboxNotification.id)).where(
                    InboxNotification.user_id == user_id, InboxNotification.deleted_at.is_(None)
                )
            )
            return InboxSummary(unread_count=unread or 0, latest_id=latest or 0)

    async def list(self, user_id: int, page: int, page_size: int, unread_only: bool) -> InboxPage:
        filters = [InboxNotification.user_id == user_id, InboxNotification.deleted_at.is_(None)]
        if unread_only:
            filters.append(InboxNotification.read_at.is_(None))
        async with get_db() as db:
            total = await db.scalar(
                select(func.count()).select_from(InboxNotification).where(*filters)
            )
            rows = (
                await db.scalars(
                    select(InboxNotification)
                    .where(*filters)
                    .order_by(InboxNotification.id.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
            items = [InboxItem.model_validate(row) for row in rows]
        return InboxPage(
            items=items,
            total=total or 0,
            page=page,
            page_size=page_size,
            summary=await self.summary(user_id),
        )

    async def read(self, user_id: int, notification_id: int) -> InboxItem | None:
        async with get_db() as db:
            row = await db.scalar(
                select(InboxNotification).where(
                    InboxNotification.id == notification_id,
                    InboxNotification.user_id == user_id,
                    InboxNotification.deleted_at.is_(None),
                )
            )
            if row is None:
                return None
            await db.execute(
                update(InboxNotification)
                .where(
                    InboxNotification.id == notification_id,
                    InboxNotification.user_id == user_id,
                    InboxNotification.read_at.is_(None),
                )
                .values(read_at=datetime.now(UTC))
            )
            await db.commit()
            await db.refresh(row)
            return InboxItem.model_validate(row)

    async def read_all(self, user_id: int, through_id: int) -> None:
        async with get_db() as db:
            await db.execute(
                update(InboxNotification)
                .where(
                    InboxNotification.user_id == user_id,
                    InboxNotification.deleted_at.is_(None),
                    InboxNotification.id <= through_id,
                    InboxNotification.read_at.is_(None),
                )
                .values(read_at=datetime.now(UTC))
            )
            await db.commit()

    async def update_selected(
        self, user_id: int, notification_ids: Sequence[int], *, remove: bool
    ) -> None:
        async with get_db() as db:
            query = update(InboxNotification).where(
                InboxNotification.user_id == user_id,
                InboxNotification.id.in_(notification_ids),
                InboxNotification.deleted_at.is_(None),
            )
            if remove:
                query = query.values(
                    deleted_at=datetime.now(UTC), title="", body="", action_path=None
                )
            else:
                query = query.where(InboxNotification.read_at.is_(None)).values(
                    read_at=datetime.now(UTC)
                )
            await db.execute(query)
            await db.commit()


INBOX = InboxRepository()
