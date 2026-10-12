import logging

import redis.asyncio as redis

from hippobox.core.settings import SETTINGS

log = logging.getLogger("redis")


class RedisManager:
    _client: redis.Redis | None = None

    @classmethod
    async def get_client(cls) -> redis.Redis:
        if cls._client is None:
            if SETTINGS.REDIS_IN_MEMORY:
                log.info("Using in-memory Redis (fakeredis).")
                try:
                    import fakeredis.aioredis as fakeredis
                except Exception as e:
                    log.error(f"fakeredis import failed: {e}")
                    raise

                client = fakeredis.FakeRedis(
                    encoding="utf-8",
                    decode_responses=True,
                )
            else:
                log.info("Connecting configured Redis")
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
