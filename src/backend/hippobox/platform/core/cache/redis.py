from contextlib import suppress

import redis.asyncio as redis

from hippobox.platform.core.config.settings import SETTINGS


class RedisManager:
    _client: redis.Redis | None = None

    @classmethod
    async def get_client(cls) -> redis.Redis:
        if cls._client is None:
            if SETTINGS.REDIS_IN_MEMORY:
                import fakeredis.aioredis as fakeredis

                client = fakeredis.FakeRedis(encoding="utf-8", decode_responses=True)
            else:
                client = redis.from_url(
                    SETTINGS.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                )
            try:
                await client.ping()
            except BaseException:
                # A failed or cancelled startup probe must not leak an unpublished pool.
                with suppress(Exception):
                    await client.aclose()
                raise
            cls._client = client
        return cls._client

    @classmethod
    async def verify_startup(cls) -> None:
        if cls._client is None:
            await cls.get_client()  # First creation already performs PING.
        else:
            await cls._client.ping()  # Existing clients need fresh evidence too.

    @classmethod
    async def close(cls) -> None:
        if cls._client is not None:
            await cls._client.aclose()
            cls._client = None
