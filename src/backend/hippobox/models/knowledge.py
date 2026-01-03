from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, ForeignKey, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from hippobox.core.database import Base, get_db


class Knowledge(Base):
    __tablename__ = "knowledge"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic: Mapped[str] = mapped_column(nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    title: Mapped[str] = mapped_column(nullable=False, unique=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


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


class KnowledgeUpdate(BaseModel):
    topic: str | None = Field(None, description="Updated topic, if changed")
    tags: list[str] | None = Field(None, description="Updated keyword list, if changed")
    title: str | None = Field(None, description="Updated title, if changed")
    content: str | None = Field(None, description="Updated content text, if changed")


class KnowledgeTable:
    async def create(self, user_id: int, form: KnowledgeForm) -> KnowledgeModel:
        async with get_db() as db:
            knowledge = Knowledge(
                user_id=user_id,
                **form.model_dump(),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(knowledge)
            await db.commit()
            await db.refresh(knowledge)
            return KnowledgeModel.model_validate(knowledge)

    async def get(self, user_id: int, knowledge_id: int) -> KnowledgeModel | None:
        async with get_db() as db:
            result = await db.execute(
                select(Knowledge).where(Knowledge.id == knowledge_id, Knowledge.user_id == user_id)
            )
            knowledge = result.scalar_one_or_none()
            return KnowledgeModel.model_validate(knowledge) if knowledge else None

    async def get_by_title(self, user_id: int, title: str) -> KnowledgeModel | None:
        async with get_db() as db:
            result = await db.execute(select(Knowledge).where(Knowledge.title == title, Knowledge.user_id == user_id))
            knowledge = result.scalar_one_or_none()
            return KnowledgeModel.model_validate(knowledge) if knowledge else None

    async def get_list(self, user_id: int) -> list[KnowledgeModel]:
        async with get_db() as db:
            result = await db.execute(select(Knowledge).where(Knowledge.user_id == user_id))
            knowledges = result.scalars().all()
            return [KnowledgeModel.model_validate(k) for k in knowledges]

    async def get_by_topic(self, user_id: int, topic: str) -> list[KnowledgeModel]:
        async with get_db() as db:
            result = await db.execute(select(Knowledge).where(Knowledge.topic == topic, Knowledge.user_id == user_id))
            knowledges = result.scalars().all()
            return [KnowledgeModel.model_validate(k) for k in knowledges]

    async def get_by_tag(self, user_id: int, tag: str) -> list[KnowledgeModel]:
        async with get_db() as db:
            result = await db.execute(
                select(Knowledge).where(Knowledge.tags.contains([tag]), Knowledge.user_id == user_id)
            )
            knowledges = result.scalars().all()
            return [KnowledgeModel.model_validate(k) for k in knowledges]

    async def update(self, user_id: int, knowledge_id: int, form: KnowledgeUpdate) -> KnowledgeModel | None:
        async with get_db() as db:
            result = await db.execute(
                select(Knowledge).where(Knowledge.id == knowledge_id, Knowledge.user_id == user_id)
            )
            knowledge = result.scalar_one_or_none()

            if knowledge is None:
                return None

            update_data = form.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(knowledge, key, value)

            knowledge.updated_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(knowledge)
            return KnowledgeModel.model_validate(knowledge)

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
            restored = Knowledge(
                id=knowledge.id,
                user_id=knowledge.user_id,
                topic=knowledge.topic,
                tags=knowledge.tags,
                title=knowledge.title,
                content=knowledge.content,
                created_at=knowledge.created_at,
                updated_at=knowledge.updated_at,
            )

            db.add(restored)
            await db.commit()
            return KnowledgeModel.model_validate(restored)


Knowledges = KnowledgeTable()
