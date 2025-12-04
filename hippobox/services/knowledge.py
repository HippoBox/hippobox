import logging

from fastapi import Request

from hippobox.errors.knowledge import KnowledgeErrorCode, KnowledgeException
from hippobox.errors.service import raise_exception_with_log
from hippobox.models.knowledge import (
    KnowledgeForm,
    KnowledgeResponse,
    Knowledges,
    KnowledgeUpdate,
)
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
    async def search(self, query: str, topic: str | None = None, tag: str | None = None, limit: int = 1):
        # embedding
        try:
            vector = self.embedding.embed(query)
        except Exception as e:
            raise_exception_with_log(KnowledgeErrorCode.EMBEDDING_FAILED, e)

        # qdrant Search
        try:
            results = self.qdrant.search("knowledge", vector, limit=limit)
        except Exception as e:
            raise_exception_with_log(KnowledgeErrorCode.QDRANT_FAILED, e)

        ids = results.get("ids", [])
        if not ids:
            return []

        # Filter SQL results + topic/tag
        knowledges = []
        for kid in ids:
            try:
                k = await Knowledges.get(kid)
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
    async def create_knowledge(self, form: KnowledgeForm):
        # SQL insert
        try:
            knowledge = await Knowledges.create(form)
        except Exception as e:
            raise_exception_with_log(KnowledgeErrorCode.CREATE_FAILED, e)

        log.info(f"SQL knowledge created (id={knowledge.id})")

        # Embedding generation
        try:
            vector = self.embedding.embed(knowledge.content)
        except Exception as e:
            # rollback
            await Knowledges.delete(knowledge.id)
            raise_exception_with_log(KnowledgeErrorCode.EMBEDDING_FAILED, e)

        # qdrant upsert
        try:
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
            # rollback
            await Knowledges.delete(knowledge.id)
            raise_exception_with_log(KnowledgeErrorCode.QDRANT_FAILED, e)

        return KnowledgeResponse.model_validate(knowledge.model_dump())

    # -------------------------------------------
    # Get
    # -------------------------------------------
    async def get_knowledge(self, kid: int):
        try:
            knowledge = await Knowledges.get(kid)
        except Exception as e:
            raise_exception_with_log(KnowledgeErrorCode.GET_FAILED, e)

        if knowledge is None:
            raise KnowledgeException(KnowledgeErrorCode.NOT_FOUND)

        return KnowledgeResponse.model_validate(knowledge.model_dump())

    async def get_knowledge_list(self):
        try:
            knowledges = await Knowledges.get_list()
        except Exception as e:
            raise_exception_with_log(KnowledgeErrorCode.GET_FAILED, e)

        return [KnowledgeResponse.model_validate(k.model_dump()) for k in knowledges]

    async def get_by_topic(self, topic: str):
        try:
            knowledges = await Knowledges.get_by_topic(topic)
        except Exception as e:
            raise_exception_with_log(KnowledgeErrorCode.GET_FAILED, e)

        return [KnowledgeResponse.model_validate(k.model_dump()) for k in knowledges]

    async def get_by_tag(self, tag: str):
        try:
            knowledges = await Knowledges.get_by_tag(tag)
        except Exception as e:
            raise_exception_with_log(KnowledgeErrorCode.GET_FAILED, e)

        return [KnowledgeResponse.model_validate(k.model_dump()) for k in knowledges]

    async def get_by_title(self, title: str):
        try:
            knowledge = await Knowledges.get_by_title(title)
        except Exception as e:
            raise_exception_with_log(KnowledgeErrorCode.GET_FAILED, e)

        if knowledge is None:
            raise KnowledgeException(KnowledgeErrorCode.NOT_FOUND)

        return KnowledgeResponse.model_validate(knowledge.model_dump())

    # -------------------------------------------
    # Update
    # -------------------------------------------
    async def update_knowledge(self, kid: int, form: KnowledgeUpdate):
        # fetch old
        try:
            old = await Knowledges.get(kid)
        except Exception as e:
            raise_exception_with_log(KnowledgeErrorCode.GET_FAILED, e)

        if old is None:
            raise KnowledgeException(KnowledgeErrorCode.NOT_FOUND)

        # update SQL
        try:
            updated = await Knowledges.update(kid, form)
        except Exception as e:
            raise_exception_with_log(KnowledgeErrorCode.UPDATE_FAILED, e)

        if updated is None:
            raise_exception_with_log(KnowledgeErrorCode.UPDATE_FAILED)

        # embedding
        try:
            vector = self.embedding.embed(updated.content)
        except Exception as e:
            # rollback
            await Knowledges.update(kid, KnowledgeUpdate(**old.model_dump()))
            raise_exception_with_log(KnowledgeErrorCode.EMBEDDING_FAILED, e)

        # qdrant upsert
        try:
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
            # rollback
            await Knowledges.update(kid, KnowledgeUpdate(**old.model_dump()))
            raise_exception_with_log(KnowledgeErrorCode.QDRANT_FAILED, e)

        return KnowledgeResponse.model_validate(updated.model_dump())

    # -------------------------------------------
    # Delete
    # -------------------------------------------
    async def delete_knowledge(self, kid: int):
        # fetch old
        try:
            old = await Knowledges.get(kid)
        except Exception as e:
            raise_exception_with_log(KnowledgeErrorCode.GET_FAILED, e)

        if old is None:
            raise KnowledgeException(KnowledgeErrorCode.NOT_FOUND)

        # SQL delete
        try:
            deleted = await Knowledges.delete(kid)
        except Exception as e:
            raise_exception_with_log(KnowledgeErrorCode.DELETE_FAILED, e)

        if not deleted:
            raise KnowledgeException(KnowledgeErrorCode.NOT_FOUND)

        # qdrant delete
        try:
            self.qdrant.delete("knowledge", [kid])
        except Exception as e:
            # rollback
            restored = await Knowledges.restore(old)
            if restored is None:
                log.error(f"Rollback failed for id={kid}")
            raise_exception_with_log(KnowledgeErrorCode.QDRANT_FAILED, e)

        return True


def get_knowledge_service(request: Request) -> KnowledgeService:
    return KnowledgeService(
        request.app.state.EMBEDDING,
        request.app.state.QDRANT,
    )
