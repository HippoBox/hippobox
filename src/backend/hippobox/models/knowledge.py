from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from hippobox.core.database import Base, get_db
from hippobox.models.topic import Topic
from hippobox.utils.knowledge_labels import (
    DEFAULT_TOPIC_NAME,
    DEFAULT_TOPIC_NORMALIZED,
    clean_label,
    normalize_label,
    normalize_tag,
    unique_labels,
)


class Tag(Base):
    __tablename__ = "tag"
    __table_args__ = (UniqueConstraint("user_id", "normalized_name", name="uq_tag_user_norm"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    knowledge_tags: Mapped[list["KnowledgeTag"]] = relationship("KnowledgeTag", back_populates="tag")


class Knowledge(Base):
    __tablename__ = "knowledge"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topic.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(nullable=False, unique=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    topic: Mapped[Topic] = relationship("Topic", back_populates="knowledge_entries")
    knowledge_tags: Mapped[list["KnowledgeTag"]] = relationship(
        "KnowledgeTag",
        back_populates="knowledge",
        cascade="all, delete-orphan",
    )


class KnowledgeTag(Base):
    __tablename__ = "knowledge_tag"

    knowledge_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tag.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    knowledge: Mapped["Knowledge"] = relationship("Knowledge", back_populates="knowledge_tags")
    tag: Mapped[Tag] = relationship("Tag", back_populates="knowledge_tags")


class KnowledgeModel(BaseModel):
    id: int = Field(..., description="Unique identifier of the knowledge entry")

    user_id: int = Field(..., description="Owner's user identifier")
    topic: str = Field(..., description="High-level topic or category of the knowledge")
    tags: list[str] = Field(default_factory=list, description="List of keywords describing the knowledge")
    title: str = Field(..., description="Short title summarizing the knowledge")
    content: str = Field(..., description="Full text content of the knowledge entry")

    created_at: datetime = Field(..., description="Timestamp when the entry was created")
    updated_at: datetime = Field(..., description="Timestamp when the entry was last updated")

    class Config:
        from_attributes = True


class KnowledgeForm(BaseModel):
    topic: str = Field(..., description="Topic or category under which the knowledge will be stored")
    tags: list[str] = Field(default_factory=list, description="Keywords for search and categorization")
    title: str = Field(..., description="A concise title summarizing the content")
    content: str = Field(..., description="The raw text body or content to be stored as knowledge")


class KnowledgeResponse(BaseModel):
    id: int = Field(..., description="Unique identifier of the knowledge entry")
    user_id: int = Field(..., description="Owner's user identifier")
    topic: str = Field(..., description="Topic or category of this knowledge")
    tags: list[str] = Field(default_factory=list, description="Keywords associated with this knowledge")
    title: str = Field(..., description="Title summarizing the content")
    content: str = Field(..., description="Full text content of the knowledge entry")
    created_at: datetime = Field(..., description="Timestamp when the entry was created")
    updated_at: datetime = Field(..., description="Timestamp when the entry was last updated")


class KnowledgeUpdate(BaseModel):
    topic: str | None = Field(None, description="Updated topic, if changed")
    tags: list[str] | None = Field(None, description="Updated keyword list, if changed")
    title: str | None = Field(None, description="Updated title, if changed")
    content: str | None = Field(None, description="Updated content text, if changed")


class KnowledgeTable:
    async def _get_or_create_default_topic(self, db, user_id: int) -> Topic:
        result = await db.execute(
            select(Topic).where(Topic.user_id == user_id, Topic.normalized_name == DEFAULT_TOPIC_NORMALIZED)
        )
        topic = result.scalar_one_or_none()
        if topic:
            return topic

        topic = Topic(
            user_id=user_id,
            name=DEFAULT_TOPIC_NAME,
            normalized_name=DEFAULT_TOPIC_NORMALIZED,
            created_at=datetime.now(timezone.utc),
        )
        db.add(topic)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            result = await db.execute(
                select(Topic).where(Topic.user_id == user_id, Topic.normalized_name == DEFAULT_TOPIC_NORMALIZED)
            )
            topic = result.scalar_one()
        return topic

    async def _get_or_create_topic(self, db, user_id: int, raw_topic: str | None) -> Topic:
        if not raw_topic or not raw_topic.strip():
            return await self._get_or_create_default_topic(db, user_id)

        name = clean_label(raw_topic)
        normalized = normalize_label(name)
        result = await db.execute(select(Topic).where(Topic.user_id == user_id, Topic.normalized_name == normalized))
        topic = result.scalar_one_or_none()
        if topic:
            return topic

        topic = Topic(user_id=user_id, name=name, normalized_name=normalized)
        db.add(topic)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            result = await db.execute(
                select(Topic).where(Topic.user_id == user_id, Topic.normalized_name == normalized)
            )
            topic = result.scalar_one()
        return topic

    async def _get_or_create_tag(self, db, user_id: int, raw_tag: str) -> Tag:
        name = clean_label(raw_tag).lstrip("#")
        normalized = normalize_tag(name)
        result = await db.execute(select(Tag).where(Tag.user_id == user_id, Tag.normalized_name == normalized))
        tag = result.scalar_one_or_none()
        if tag:
            return tag

        tag = Tag(user_id=user_id, name=name, normalized_name=normalized)
        db.add(tag)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            result = await db.execute(select(Tag).where(Tag.user_id == user_id, Tag.normalized_name == normalized))
            tag = result.scalar_one()
        return tag

    def _to_model(self, knowledge: Knowledge) -> KnowledgeModel:
        topic_name = knowledge.topic.name if knowledge.topic else DEFAULT_TOPIC_NAME
        tags = [kt.tag.name for kt in knowledge.knowledge_tags if kt.tag]
        return KnowledgeModel(
            id=knowledge.id,
            user_id=knowledge.user_id,
            topic=topic_name,
            tags=tags,
            title=knowledge.title,
            content=knowledge.content,
            created_at=knowledge.created_at,
            updated_at=knowledge.updated_at,
        )

    async def create(self, user_id: int, form: KnowledgeForm) -> KnowledgeModel:
        async with get_db() as db:
            topic = await self._get_or_create_topic(db, user_id, form.topic)
            knowledge = Knowledge(
                user_id=user_id,
                topic_id=topic.id,
                title=form.title.strip(),
                content=form.content,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            knowledge.topic = topic
            db.add(knowledge)
            await db.flush()

            tag_names = unique_labels(form.tags)
            if tag_names:
                for raw_tag in tag_names:
                    tag = await self._get_or_create_tag(db, user_id, raw_tag)
                    db.add(KnowledgeTag(knowledge_id=knowledge.id, tag_id=tag.id, user_id=user_id))

            await db.commit()
            result = await db.execute(
                select(Knowledge)
                .options(
                    selectinload(Knowledge.topic),
                    selectinload(Knowledge.knowledge_tags).selectinload(KnowledgeTag.tag),
                )
                .where(Knowledge.id == knowledge.id, Knowledge.user_id == user_id)
            )
            created = result.scalar_one()
            return self._to_model(created)

    async def get(self, user_id: int, knowledge_id: int) -> KnowledgeModel | None:
        async with get_db() as db:
            result = await db.execute(
                select(Knowledge)
                .options(
                    selectinload(Knowledge.topic),
                    selectinload(Knowledge.knowledge_tags).selectinload(KnowledgeTag.tag),
                )
                .where(Knowledge.id == knowledge_id, Knowledge.user_id == user_id)
            )
            knowledge = result.scalar_one_or_none()
            return self._to_model(knowledge) if knowledge else None

    async def get_by_title(self, user_id: int, title: str) -> KnowledgeModel | None:
        async with get_db() as db:
            result = await db.execute(
                select(Knowledge)
                .options(
                    selectinload(Knowledge.topic),
                    selectinload(Knowledge.knowledge_tags).selectinload(KnowledgeTag.tag),
                )
                .where(Knowledge.title == title, Knowledge.user_id == user_id)
            )
            knowledge = result.scalar_one_or_none()
            return self._to_model(knowledge) if knowledge else None

    async def get_list(self, user_id: int) -> list[KnowledgeModel]:
        async with get_db() as db:
            result = await db.execute(
                select(Knowledge)
                .options(
                    selectinload(Knowledge.topic),
                    selectinload(Knowledge.knowledge_tags).selectinload(KnowledgeTag.tag),
                )
                .where(Knowledge.user_id == user_id)
            )
            knowledges = result.scalars().all()
            return [self._to_model(k) for k in knowledges]

    async def get_by_topic(self, user_id: int, topic: str) -> list[KnowledgeModel]:
        async with get_db() as db:
            normalized = normalize_label(topic)
            result = await db.execute(
                select(Knowledge)
                .join(Topic, Knowledge.topic_id == Topic.id)
                .options(
                    selectinload(Knowledge.topic),
                    selectinload(Knowledge.knowledge_tags).selectinload(KnowledgeTag.tag),
                )
                .where(Topic.normalized_name == normalized, Knowledge.user_id == user_id)
            )
            knowledges = result.scalars().all()
            return [self._to_model(k) for k in knowledges]

    async def get_by_tag(self, user_id: int, tag: str) -> list[KnowledgeModel]:
        async with get_db() as db:
            normalized = normalize_tag(tag)
            result = await db.execute(
                select(Knowledge)
                .join(KnowledgeTag, Knowledge.id == KnowledgeTag.knowledge_id)
                .join(Tag, Tag.id == KnowledgeTag.tag_id)
                .options(
                    selectinload(Knowledge.topic),
                    selectinload(Knowledge.knowledge_tags).selectinload(KnowledgeTag.tag),
                )
                .where(Tag.normalized_name == normalized, Knowledge.user_id == user_id)
            )
            knowledges = result.scalars().all()
            return [self._to_model(k) for k in knowledges]

    async def update(self, user_id: int, knowledge_id: int, form: KnowledgeUpdate) -> KnowledgeModel | None:
        async with get_db() as db:
            result = await db.execute(
                select(Knowledge)
                .options(
                    selectinload(Knowledge.topic),
                    selectinload(Knowledge.knowledge_tags).selectinload(KnowledgeTag.tag),
                )
                .where(Knowledge.id == knowledge_id, Knowledge.user_id == user_id)
            )
            knowledge = result.scalar_one_or_none()

            if knowledge is None:
                return None

            update_data = form.model_dump(exclude_unset=True)
            if "topic" in update_data:
                topic = await self._get_or_create_topic(db, user_id, update_data.pop("topic"))
                knowledge.topic_id = topic.id
                knowledge.topic = topic

            if "tags" in update_data:
                tags = update_data.pop("tags") or []
                knowledge.knowledge_tags.clear()
                tag_names = unique_labels(tags)
                for raw_tag in tag_names:
                    tag = await self._get_or_create_tag(db, user_id, raw_tag)
                    knowledge.knowledge_tags.append(
                        KnowledgeTag(knowledge_id=knowledge.id, tag_id=tag.id, user_id=user_id)
                    )

            for key, value in update_data.items():
                setattr(knowledge, key, value)

            knowledge.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(knowledge)
            return self._to_model(knowledge)

    async def delete(self, user_id: int, knowledge_id: int) -> bool:
        async with get_db() as db:
            result = await db.execute(
                select(Knowledge).where(Knowledge.id == knowledge_id, Knowledge.user_id == user_id)
            )
            knowledge = result.scalar_one_or_none()

            if knowledge is None:
                return False

            await db.delete(knowledge)
            await db.commit()
            return True

    async def restore(self, knowledge: KnowledgeModel) -> KnowledgeModel:
        async with get_db() as db:
            topic = await self._get_or_create_topic(db, knowledge.user_id, knowledge.topic)
            restored = Knowledge(
                id=knowledge.id,
                user_id=knowledge.user_id,
                topic_id=topic.id,
                title=knowledge.title,
                content=knowledge.content,
                created_at=knowledge.created_at,
                updated_at=knowledge.updated_at,
            )
            restored.topic = topic

            db.add(restored)
            await db.flush()
            tag_names = unique_labels(knowledge.tags)
            for raw_tag in tag_names:
                tag = await self._get_or_create_tag(db, knowledge.user_id, raw_tag)
                restored.knowledge_tags.append(
                    KnowledgeTag(knowledge_id=restored.id, tag_id=tag.id, user_id=knowledge.user_id)
                )
            await db.commit()
            await db.refresh(restored)
            return self._to_model(restored)


Knowledges = KnowledgeTable()
