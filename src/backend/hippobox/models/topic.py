from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hippobox.core.database import Base, get_db
from hippobox.utils.knowledge_labels import DEFAULT_TOPIC_NORMALIZED, clean_label, normalize_label

# for sqlalchemy type checking
if TYPE_CHECKING:
    from hippobox.models.knowledge import Knowledge


class Topic(Base):
    __tablename__ = "topic"
    __table_args__ = (UniqueConstraint("user_id", "normalized_name", name="uq_topic_user_norm"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    knowledge_entries: Mapped[list["Knowledge"]] = relationship("Knowledge", back_populates="topic")


class TopicForm(BaseModel):
    name: str = Field(..., description="Topic name")


class TopicUpdate(BaseModel):
    name: str | None = Field(None, description="Updated topic name")


class TopicResponse(BaseModel):
    id: int = Field(..., description="Topic identifier")
    user_id: int = Field(..., description="Owner's user identifier")
    name: str = Field(..., description="Topic name")
    is_default: bool = Field(False, description="Whether this is the default topic")
    created_at: datetime = Field(..., description="Timestamp when the topic was created")


class TopicTable:
    def _to_model(self, topic: Topic) -> TopicResponse:
        return TopicResponse(
            id=topic.id,
            user_id=topic.user_id,
            name=topic.name,
            is_default=topic.normalized_name == DEFAULT_TOPIC_NORMALIZED,
            created_at=topic.created_at,
        )

    async def get(self, user_id: int, topic_id: int) -> TopicResponse | None:
        async with get_db() as db:
            result = await db.execute(select(Topic).where(Topic.id == topic_id, Topic.user_id == user_id))
            topic = result.scalar_one_or_none()
            return self._to_model(topic) if topic else None

    async def list(self, user_id: int) -> list[TopicResponse]:
        async with get_db() as db:
            result = await db.execute(
                select(Topic).where(Topic.user_id == user_id).order_by(Topic.normalized_name.asc())
            )
            topics = result.scalars().all()
            return [self._to_model(topic) for topic in topics]

    async def create(self, user_id: int, name: str) -> TopicResponse:
        async with get_db() as db:
            cleaned = clean_label(name)
            topic = Topic(
                user_id=user_id,
                name=cleaned,
                normalized_name=normalize_label(cleaned),
                created_at=datetime.now(timezone.utc),
            )
            db.add(topic)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                raise
            await db.refresh(topic)
            return self._to_model(topic)

    async def update(self, user_id: int, topic_id: int, name: str) -> TopicResponse | None:
        async with get_db() as db:
            result = await db.execute(select(Topic).where(Topic.id == topic_id, Topic.user_id == user_id))
            topic = result.scalar_one_or_none()
            if topic is None:
                return None

            cleaned = clean_label(name)
            topic.name = cleaned
            if topic.normalized_name != DEFAULT_TOPIC_NORMALIZED:
                topic.normalized_name = normalize_label(cleaned)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                raise
            await db.refresh(topic)
            return self._to_model(topic)

    async def delete(self, user_id: int, topic_id: int) -> bool:
        async with get_db() as db:
            result = await db.execute(select(Topic).where(Topic.id == topic_id, Topic.user_id == user_id))
            topic = result.scalar_one_or_none()
            if topic is None:
                return False

            await db.delete(topic)
            await db.commit()
            return True


Topics = TopicTable()
