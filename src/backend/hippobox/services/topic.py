import logging

from fastapi import Request
from sqlalchemy.exc import IntegrityError

from hippobox.errors.service import raise_exception_with_log
from hippobox.errors.topic import TopicErrorCode, TopicException
from hippobox.models.topic import TopicResponse, Topics, TopicUpdate

log = logging.getLogger("topic")


def _normalize(value: str) -> str:
    return " ".join(value.strip().split())


class TopicService:
    async def list_topics(self, user_id: int) -> list[TopicResponse]:
        try:
            return await Topics.list(user_id)
        except Exception as e:
            log.error(f"Failed to list topics for user {user_id}: {e}")
            return []

    async def create_topic(self, user_id: int, name: str) -> TopicResponse:
        cleaned = _normalize(name)
        if not cleaned:
            raise TopicException(TopicErrorCode.INVALID_NAME)

        try:
            return await Topics.create(user_id, cleaned)
        except IntegrityError:
            raise TopicException(TopicErrorCode.NAME_EXISTS)
        except Exception as e:
            raise_exception_with_log(TopicErrorCode.CREATE_FAILED, e)

    async def update_topic(self, user_id: int, topic_id: int, form: TopicUpdate) -> TopicResponse:
        if not form.name or not _normalize(form.name):
            raise TopicException(TopicErrorCode.INVALID_NAME)

        try:
            updated = await Topics.update(user_id, topic_id, form.name)
        except IntegrityError:
            raise TopicException(TopicErrorCode.NAME_EXISTS)
        except Exception as e:
            raise_exception_with_log(TopicErrorCode.UPDATE_FAILED, e)
            return None  # unreachable

        if updated is None:
            raise TopicException(TopicErrorCode.NOT_FOUND)
        return updated

    async def delete_topic(self, user_id: int, topic_id: int) -> None:
        topic = await Topics.get(user_id, topic_id)
        if topic is None:
            raise TopicException(TopicErrorCode.NOT_FOUND)
        if topic.is_default:
            raise TopicException(TopicErrorCode.DELETE_DEFAULT)

        try:
            success = await Topics.delete(user_id, topic_id)
        except Exception as e:
            raise_exception_with_log(TopicErrorCode.DELETE_FAILED, e)
            return

        if not success:
            raise TopicException(TopicErrorCode.DELETE_FAILED)


def get_topic_service(request: Request) -> TopicService:
    return TopicService()
