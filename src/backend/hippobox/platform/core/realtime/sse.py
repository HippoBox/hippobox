import time
from collections.abc import AsyncIterator

from fastapi import Request

from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.observability.logging import get_logger
from hippobox.platform.core.realtime.broker import RealtimeBroker
from hippobox.platform.core.realtime.events import RealtimeEventType, build_realtime_event, encode_sse_event
from hippobox.platform.models.user import UserResponse

logger = get_logger("hippobox.platform.core.realtime.sse")


async def stream_user_events(
    *,
    request: Request,
    current_user: UserResponse,
    last_event_id: str | None,
) -> AsyncIterator[str]:
    heartbeat_seconds = max(5, SETTINGS.SSE_HEARTBEAT_SECONDS)
    retry_millis = max(1000, SETTINGS.SSE_RETRY_MILLIS)
    poll_seconds = 1.0

    if last_event_id:
        # Future extension point: replay by Last-Event-ID.
        logger.debug(
            "SSE reconnect requested (user_id=%s, last_event_id=%s).",
            current_user.id,
            last_event_id,
        )

    pubsub = await RealtimeBroker.subscribe_user_events(user_id=current_user.id)
    user_channel = RealtimeBroker.build_user_channel(current_user.id)
    last_heartbeat_at = time.monotonic()

    try:
        connected_event = build_realtime_event(
            RealtimeEventType.CONNECTED,
            {"user_id": current_user.id, "channel": user_channel},
        )
        yield encode_sse_event(connected_event, retry_millis=retry_millis)

        while True:
            if await request.is_disconnected():
                logger.debug("SSE disconnected by client (user_id=%s).", current_user.id)
                break

            event = await RealtimeBroker.read_event(pubsub, timeout_seconds=poll_seconds)
            if event is not None:
                yield encode_sse_event(event)
                continue

            now = time.monotonic()
            if now - last_heartbeat_at >= heartbeat_seconds:
                heartbeat = build_realtime_event(RealtimeEventType.PING)
                yield encode_sse_event(heartbeat)
                last_heartbeat_at = now
    finally:
        await pubsub.unsubscribe(user_channel)
        await RealtimeBroker.close_subscription(pubsub)
