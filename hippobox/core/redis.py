import logging

import redis.asyncio as redis

from hippobox.core.settings import SETTINGS

log = logging.getLogger("redis")


class RedisManager:
    _client: redis.Redis | None = None

    @classmethod
    async def get_client(cls) -> redis.Redis:
        if cls._client is None:
            log.info(f"Connecting Redis → {SETTINGS.REDIS_URL}")

            client = redis.from_url(
                SETTINGS.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )

            try:
                await client.ping()
                log.info("Redis connection established.")
            except Exception as e:
                log.error(f"Redis connection failed: {e}")
                raise

            cls._client = client

        return cls._client

    @classmethod
    async def close(cls):
        if cls._client:
            log.info("Closing Redis connection...")
            await cls._client.aclose()
            cls._client = None
            log.info("Redis closed.")
