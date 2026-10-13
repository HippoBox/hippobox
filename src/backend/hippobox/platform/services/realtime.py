import asyncio
from collections.abc import AsyncIterator, Mapping
from enum import StrEnum
from typing import Any

from fastapi import Request
from redis.exceptions import RedisError

from hippobox.platform.core.observability.logging import get_logger
from hippobox.platform.core.realtime.broker import RealtimeBroker
from hippobox.platform.core.realtime.events import build_realtime_event
from hippobox.platform.core.realtime.sse import stream_user_events
from hippobox.platform.models.user import UserResponse

logger = get_logger("service.realtime")
NOTIFICATION_TIMEOUT_SECONDS = 2


class RealtimeService:
    def stream_user_events(
        self,
        *,
        request: Request,
        current_user: UserResponse,
        last_event_id: str | None,
    ) -> AsyncIterator[str]:
        return stream_user_events(
            request=request,
            current_user=current_user,
            last_event_id=last_event_id,
        )

    async def publish_user_event(
        self,
        *,
        user_id: int,
        event_type: StrEnum | str,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        event = build_realtime_event(event_type, payload)
        await RealtimeBroker.publish_user_event(user_id=user_id, event=event)

    async def publish_user_notification(
        self,
        *,
        user_id: int,
        event_type: StrEnum | str,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        """Best-effort UI notification after commit; never use for durable domain work."""
        event = build_realtime_event(event_type, payload)
        try:
            async with asyncio.timeout(NOTIFICATION_TIMEOUT_SECONDS):
                await RealtimeBroker.publish_user_event(user_id=user_id, event=event)
        except (RedisError, OSError, TimeoutError) as error:
            logger.warning(
                "Realtime notification failed after commit (user_id=%s, event_type=%s, error_type=%s).",
                user_id,
                event_type,
                type(error).__name__,
            )
