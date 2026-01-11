import logging

from fastapi import Request
from sqlalchemy.exc import IntegrityError

from hippobox.errors.knowledge import KnowledgeErrorCode, KnowledgeException
from hippobox.errors.service import raise_exception_with_log
from hippobox.models.knowledge import KnowledgeForm, KnowledgeResponse, Knowledges, KnowledgeUpdate
from hippobox.rag.embedding import Embedding
from hippobox.rag.qdrant import Qdrant
from hippobox.utils.preprocess import preprocess_content

log = logging.getLogger("knowledge")


class KnowledgeService:
    def __init__(self, embedding: Embedding, qdrant: Qdrant):
        self.embedding = embedding
        self.qdrant = qdrant

    # -------------------------------------------
    # Search
    # -------------------------------------------
    async def search(
        self, user_id: int, query: str, topic: str | None = None, tag: str | None = None, limit: int = 1
    ) -> list[KnowledgeResponse]:
        vector = self.embedding.embed(query)
        results = self.qdrant.search("knowledge", vector, limit=limit)

        ids = results.get("ids", [])
        if not ids:
            return []

        knowledges = []
        for kid in ids:
            try:
                k = await Knowledges.get(user_id, kid)
            except Exception as e:
                log.exception(f"{KnowledgeErrorCode.GET_FAILED.default_message}: {e}")
                continue

            if k is None:
                continue
            if topic and k.topic != topic:
                continue
            if tag and tag not in k.tags:
                continue

            knowledges.append(KnowledgeResponse.model_validate(k.model_dump()))

        return knowledges

    # -------------------------------------------
    # Create
    # -------------------------------------------
    async def create_knowledge(self, user_id: int, form: KnowledgeForm) -> KnowledgeResponse:
        try:
            knowledge = await Knowledges.create(user_id, form)
        except IntegrityError:
            raise KnowledgeException(KnowledgeErrorCode.TITLE_EXISTS)
        except Exception as e:
            raise_exception_with_log(KnowledgeErrorCode.CREATE_FAILED, e)

        log.info(f"SQL knowledge created (id={knowledge.id})")

        try:
            vector = self.embedding.embed(knowledge.content)
            self.qdrant.upsert(
                "knowledge",
                [
                    {
                        "id": knowledge.id,
                        "vector": vector,
                        "text": preprocess_content(knowledge),
                        "metadata": {
                            "topic": knowledge.topic,
                            "tags": knowledge.tags,
                            "title": knowledge.title,
                            "created_at": str(knowledge.created_at),
                        },
                    }
                ],
            )
        except Exception as e:
            await Knowledges.delete(user_id, knowledge.id)
            raise_exception_with_log(KnowledgeErrorCode.CREATE_FAILED, e)

        return KnowledgeResponse.model_validate(knowledge.model_dump())

    # -------------------------------------------
    # Get
    # -------------------------------------------
    async def get_knowledge(self, user_id: int, kid: int) -> KnowledgeResponse:
        knowledge = await Knowledges.get(user_id, kid)

        if knowledge is None:
            raise KnowledgeException(KnowledgeErrorCode.NOT_FOUND)

        return KnowledgeResponse.model_validate(knowledge.model_dump())

    async def get_knowledge_list(self, user_id: int) -> list[KnowledgeResponse]:
        knowledges = await Knowledges.get_list(user_id)
        return [KnowledgeResponse.model_validate(k.model_dump()) for k in knowledges]

    async def get_by_topic(self, user_id: int, topic: str) -> list[KnowledgeResponse]:
        knowledges = await Knowledges.get_by_topic(user_id, topic)
        return [KnowledgeResponse.model_validate(k.model_dump()) for k in knowledges]

    async def get_by_tag(self, user_id: int, tag: str) -> list[KnowledgeResponse]:
        knowledges = await Knowledges.get_by_tag(user_id, tag)
        return [KnowledgeResponse.model_validate(k.model_dump()) for k in knowledges]

    async def get_by_title(self, user_id: int, title: str) -> KnowledgeResponse:
        knowledge = await Knowledges.get_by_title(user_id, title)

        if knowledge is None:
            raise KnowledgeException(KnowledgeErrorCode.NOT_FOUND)

        return KnowledgeResponse.model_validate(knowledge.model_dump())

    # -------------------------------------------
    # Update
    # -------------------------------------------
    async def update_knowledge(self, user_id: int, kid: int, form: KnowledgeUpdate) -> KnowledgeResponse:
        old = await Knowledges.get(user_id, kid)

        if old is None:
            raise KnowledgeException(KnowledgeErrorCode.UPDATE_FAILED)

        try:
            updated = await Knowledges.update(user_id, kid, form)
            if updated is None:
                raise_exception_with_log(KnowledgeErrorCode.UPDATE_FAILED)
        except IntegrityError:
            raise KnowledgeException(KnowledgeErrorCode.TITLE_EXISTS)
        except Exception as e:
            raise_exception_with_log(KnowledgeErrorCode.UPDATE_FAILED, e)

        try:
            vector = self.embedding.embed(updated.content)
            self.qdrant.upsert(
                "knowledge",
                [
                    {
                        "id": updated.id,
                        "vector": vector,
                        "text": preprocess_content(updated),
                        "metadata": {
                            "topic": updated.topic,
                            "tags": updated.tags,
                            "title": updated.title,
                            "created_at": str(updated.created_at),
                        },
                    }
                ],
            )
        except Exception as e:
            try:
                await Knowledges.update(
                    user_id,
                    kid,
                    KnowledgeUpdate(
                        topic=old.topic,
                        tags=old.tags,
                        title=old.title,
                        content=old.content,
                    ),
                    override_updated_at=old.updated_at,
                )
            except Exception as rollback_error:
                log.exception(f"Rollback failed for id={kid}: {rollback_error}")
            raise_exception_with_log(KnowledgeErrorCode.UPDATE_FAILED, e)

        return KnowledgeResponse.model_validate(updated.model_dump())

    # -------------------------------------------
    # Delete
    # -------------------------------------------
    async def delete_knowledge(self, user_id: int, kid: int) -> bool:
        old = await Knowledges.get(user_id, kid)
        if old is None:
            raise KnowledgeException(KnowledgeErrorCode.DELETE_FAILED)

        try:
            deleted = await Knowledges.delete(user_id, kid)
            if not deleted:
                raise KnowledgeException(KnowledgeErrorCode.DELETE_FAILED)

            self.qdrant.delete("knowledge", [kid])
        except Exception as e:
            restored = await Knowledges.restore(old)
            if restored is None:
                log.error(f"Rollback failed for id={kid}")
                raise KnowledgeException(KnowledgeErrorCode.DELETE_FAILED)
            raise_exception_with_log(KnowledgeErrorCode.DELETE_FAILED, e)

        return True


def get_knowledge_service(request: Request) -> KnowledgeService:
    return KnowledgeService(
        request.app.state.EMBEDDING,
        request.app.state.QDRANT,
    )
