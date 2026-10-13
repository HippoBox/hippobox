import inspect

from redis.asyncio.client import PubSub

from hippobox.platform.core.cache.redis import RedisManager
from hippobox.platform.core.observability.logging import get_logger
from hippobox.platform.core.realtime.events import RealtimeEvent

logger = get_logger("hippobox.platform.core.realtime.broker")


class RealtimeBroker:
    USER_CHANNEL_PREFIX = "realtime:user"

    @classmethod
    def build_user_channel(cls, user_id: int) -> str:
        return f"{cls.USER_CHANNEL_PREFIX}:{user_id}"

    @classmethod
    async def publish_user_event(cls, *, user_id: int, event: RealtimeEvent) -> None:
        redis_client = await RedisManager.get_client()
        channel = cls.build_user_channel(user_id)
        await redis_client.publish(channel, event.model_dump_json())

    @classmethod
    async def subscribe_user_events(cls, *, user_id: int) -> PubSub:
        redis_client = await RedisManager.get_client()
        channel = cls.build_user_channel(user_id)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    @staticmethod
    async def read_event(pubsub: PubSub, *, timeout_seconds: float) -> RealtimeEvent | None:
        message = await pubsub.get_message(
            ignore_subscribe_messages=True,
            timeout=timeout_seconds,
        )
        if message is None:
            return None

        raw_data = message.get("data")
        if not isinstance(raw_data, str):
            return None

        try:
            return RealtimeEvent.model_validate_json(raw_data)
        except Exception:
            logger.exception("Failed to decode realtime event payload.")
            return None

    @staticmethod
    async def close_subscription(pubsub: PubSub) -> None:
        close_method = getattr(pubsub, "aclose", None)
        if callable(close_method):
            await close_method()
            return

        fallback_close = getattr(pubsub, "close", None)
        if callable(fallback_close):
            maybe_awaitable = fallback_close()
            if inspect.isawaitable(maybe_awaitable):
                await maybe_awaitable
