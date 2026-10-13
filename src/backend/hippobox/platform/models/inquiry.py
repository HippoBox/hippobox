"""Private support conversations and transactional inbox delivery."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from hippobox.platform.core.db.session import Base, get_db
from hippobox.platform.core.error.inquiry_exception import InquiryErrorCode, InquiryException
from hippobox.platform.models.inbox import add_inbox_notification
from hippobox.platform.models.pagination import PageResponse
from hippobox.platform.models.user import User


class InquiryStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class Inquiry(Base):
    __tablename__ = "inquiries"
    __table_args__ = (
        UniqueConstraint("user_id", "request_id", name="uq_inquiry_request"),
        Index("ix_inquiry_owner_updated", "user_id", "updated_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class InquiryMessage(Base):
    __tablename__ = "inquiry_messages"
    __table_args__ = (
        UniqueConstraint("inquiry_id", "request_id", name="uq_inquiry_message_request"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inquiry_id: Mapped[int] = mapped_column(
        ForeignKey("inquiries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[int | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    author_role: Mapped[str] = mapped_column(String(10), nullable=False)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class InquiryCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    request_id: UUID
    subject: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=4000)


class InquiryReply(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    request_id: UUID
    body: str = Field(min_length=1, max_length=4000)


class InquiryStatusForm(BaseModel):
    status: InquiryStatus


class InquiryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subject: str
    status: InquiryStatus
    created_at: datetime
    updated_at: datetime
    requester_name: str
    requester_email: str


class InquiryMessageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    author_role: str
    body: str
    created_at: datetime


class InquiryDetail(InquiryItem):
    messages: list[InquiryMessageItem]


class InquiryPage(PageResponse[InquiryItem]):
    pass


async def _item(db: AsyncSession, row: Inquiry) -> dict:
    owner = await db.get(User, row.user_id)
    return dict(
        id=row.id,
        subject=row.subject,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        requester_name=owner.name,
        requester_email=owner.email,
    )


async def _notify(
    db: AsyncSession, row: Inquiry, *, kind: str, admins: bool, owner: bool
) -> list[int]:
    recipients = (
        set(await db.scalars(select(User.id).where(User.role == "admin", User.is_active.is_(True))))
        if admins
        else set()
    )
    if owner:
        recipients.add(row.user_id)
    for user_id in recipients:
        path = (
            f"/settings?section=support&inquiry={row.id}"
            if user_id == row.user_id
            else f"/admin/inquiries?inquiry={row.id}"
        )
        await add_inbox_notification(
            db,
            user_id=user_id,
            kind=kind,
            title="Support request updated",
            body=row.subject,
            action_path=path,
        )
    return list(recipients)


class InquiryRepository:
    async def list(
        self, user_id: int, admin: bool, page: int, page_size: int, status: InquiryStatus | None
    ) -> InquiryPage:
        filters = [] if admin else [Inquiry.user_id == user_id]
        if status:
            filters.append(Inquiry.status == status)
        async with get_db() as db:
            total = await db.scalar(select(func.count()).select_from(Inquiry).where(*filters))
            rows = (
                await db.scalars(
                    select(Inquiry)
                    .where(*filters)
                    .order_by(Inquiry.updated_at.desc(), Inquiry.id.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
            items = [InquiryItem(**await _item(db, row)) for row in rows]
            return InquiryPage(items=items, total=total or 0, page=page, page_size=page_size)

    async def _get(
        self, db: AsyncSession, inquiry_id: int, user_id: int, admin: bool, lock: bool = False
    ) -> Inquiry:
        query = select(Inquiry).where(Inquiry.id == inquiry_id)
        if not admin:
            query = query.where(Inquiry.user_id == user_id)
        if lock:
            query = query.with_for_update()
        row = await db.scalar(query)
        if row is None:
            raise InquiryException(InquiryErrorCode.NOT_FOUND)
        return row

    async def detail(self, inquiry_id: int, user_id: int, admin: bool) -> InquiryDetail:
        async with get_db() as db:
            row = await self._get(db, inquiry_id, user_id, admin)
            messages = (
                await db.scalars(
                    select(InquiryMessage)
                    .where(InquiryMessage.inquiry_id == row.id)
                    .order_by(InquiryMessage.id)
                )
            ).all()
            return InquiryDetail(
                **await _item(db, row),
                messages=[InquiryMessageItem.model_validate(message) for message in messages],
            )

    async def create(self, user_id: int, form: InquiryCreate) -> tuple[int, list[int]]:
        async with get_db() as db:
            # Lock the existing owner to serialize concurrent retries for the same request key.
            await db.scalar(select(User.id).where(User.id == user_id).with_for_update())
            prior = await db.scalar(
                select(Inquiry).where(
                    Inquiry.user_id == user_id, Inquiry.request_id == str(form.request_id)
                )
            )
            if prior:
                return prior.id, []
            row = Inquiry(user_id=user_id, request_id=str(form.request_id), subject=form.subject)
            db.add(row)
            await db.flush()
            db.add(
                InquiryMessage(
                    inquiry_id=row.id,
                    author_id=user_id,
                    author_role="user",
                    request_id=str(form.request_id),
                    body=form.body,
                )
            )
            recipients = await _notify(db, row, kind="inquiry_received", admins=True, owner=True)
            await db.commit()
            return row.id, recipients

    async def reply(
        self, inquiry_id: int, user_id: int, admin: bool, form: InquiryReply
    ) -> list[int]:
        async with get_db() as db:
            row = await self._get(db, inquiry_id, user_id, admin, lock=True)
            prior = await db.scalar(
                select(InquiryMessage).where(
                    InquiryMessage.inquiry_id == row.id,
                    InquiryMessage.request_id == str(form.request_id),
                )
            )
            if prior:
                return []
            if row.status == InquiryStatus.CLOSED:
                raise InquiryException(InquiryErrorCode.CLOSED)
            count = await db.scalar(
                select(func.count())
                .select_from(InquiryMessage)
                .where(InquiryMessage.inquiry_id == row.id)
            )
            if count >= 200:
                raise InquiryException(InquiryErrorCode.THREAD_FULL)
            db.add(
                InquiryMessage(
                    inquiry_id=row.id,
                    author_id=user_id,
                    author_role="admin" if admin else "user",
                    request_id=str(form.request_id),
                    body=form.body,
                )
            )
            row.updated_at = datetime.now(UTC)
            recipients = await _notify(db, row, kind="inquiry_reply", admins=not admin, owner=admin)
            await db.commit()
            return recipients

    async def status(self, inquiry_id: int, user_id: int, status: InquiryStatus) -> list[int]:
        async with get_db() as db:
            row = await self._get(db, inquiry_id, user_id, True, lock=True)
            if row.status == status:
                return []
            row.status = status
            row.updated_at = datetime.now(UTC)
            recipients = await _notify(db, row, kind="inquiry_status", admins=False, owner=True)
            await db.commit()
            return recipients


INQUIRIES = InquiryRepository()
