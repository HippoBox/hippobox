import logging
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt

from hippobox.core.redis import RedisManager
from hippobox.core.settings import SETTINGS

log = logging.getLogger("utils.token")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SETTINGS.SECRET_KEY, algorithm=SETTINGS.ALGORITHM)
    return encoded_jwt


def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)


async def store_refresh_token(user_id: int, refresh_token: str) -> None:
    try:
        redis = await RedisManager.get_client()
        key = f"refresh_token:{user_id}"

        expire_days = getattr(SETTINGS, "REFRESH_TOKEN_EXPIRE_DAYS", 7)

        await redis.setex(key, timedelta(days=expire_days), refresh_token)
    except Exception as e:
        log.error(f"Failed to save refresh token to Redis for user {user_id}: {e}")
        raise


async def verify_refresh_token(user_id: int, token_to_verify: str) -> bool:
    try:
        redis = await RedisManager.get_client()
        key = f"refresh_token:{user_id}"

        stored_token = await redis.get(key)

        if not stored_token:
            return False

        if isinstance(stored_token, bytes):
            stored_token = stored_token.decode("utf-8")

        return stored_token == token_to_verify

    except Exception as e:
        log.error(f"Failed to verify refresh token for user {user_id}: {e}")
        return False


async def delete_refresh_token(user_id: int) -> None:
    try:
        redis = await RedisManager.get_client()
        key = f"refresh_token:{user_id}"
        await redis.delete(key)
    except Exception as e:
        log.error(f"Failed to delete refresh token for user {user_id}: {e}")
