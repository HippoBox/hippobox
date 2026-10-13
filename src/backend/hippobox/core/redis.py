"""Blueprint Redis lifecycle shared by all HippoBox services."""

from hippobox.platform.core.cache.redis import RedisManager

__all__ = ["RedisManager"]
