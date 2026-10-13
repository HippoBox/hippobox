import json
import secrets
from datetime import UTC, datetime, timedelta

from jose import jwt
from redis.exceptions import WatchError

from hippobox.platform.core.cache.redis import RedisManager
from hippobox.platform.core.config.settings import SETTINGS


def create_access_token(subject: str, email: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "email": email, "exp": expire}
    return jwt.encode(payload, SETTINGS.SECRET_KEY, algorithm=SETTINGS.ALGORITHM)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def create_refresh_session_id() -> str:
    return secrets.token_urlsafe(24)


def create_email_verification_token() -> str:
    return secrets.token_urlsafe(32)


def create_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def _refresh_session_key(session_id: str) -> str:
    return f"refresh_session:{session_id}"


def _refresh_user_sessions_key(user_id: int) -> str:
    return f"refresh_user_sessions:{user_id}"


async def store_refresh_token(
    user_id: int,
    session_id: str,
    refresh_token: str,
    remember_me: bool = False,
) -> None:
    redis = await RedisManager.get_client()
    ttl = timedelta(days=SETTINGS.REFRESH_TOKEN_EXPIRE_DAYS)
    session_payload = json.dumps(
        {
            "user_id": user_id,
            "refresh_token": refresh_token,
            "remember_me": remember_me,
        }
    )
    await redis.setex(
        _refresh_session_key(session_id),
        ttl,
        session_payload,
    )
    await redis.sadd(_refresh_user_sessions_key(user_id), session_id)
    await redis.expire(_refresh_user_sessions_key(user_id), ttl)


async def get_refresh_session(session_id: str) -> tuple[int, bool] | None:
    redis = await RedisManager.get_client()
    raw_session = await redis.get(_refresh_session_key(session_id))
    if raw_session is None:
        return None

    try:
        session_data = json.loads(raw_session)
        user_id = int(session_data.get("user_id"))
        remember_me = bool(session_data.get("remember_me", False))
    except (TypeError, ValueError):
        return None

    return user_id, remember_me


async def store_email_verification_token(user_id: int, token: str) -> None:
    redis = await RedisManager.get_client()
    ttl = timedelta(minutes=SETTINGS.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES)
    user_token_key = f"email_verify_user_token:{user_id}"

    previous_token = await redis.get(user_token_key)
    if previous_token:
        await redis.delete(f"email_verify_token:{previous_token}")

    await redis.setex(f"email_verify_token:{token}", ttl, str(user_id))
    await redis.setex(user_token_key, ttl, token)


async def store_password_reset_token(user_id: int, token: str) -> None:
    redis = await RedisManager.get_client()
    ttl = timedelta(minutes=SETTINGS.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    user_token_key = f"password_reset_user_token:{user_id}"

    previous_token = await redis.get(user_token_key)
    if previous_token:
        await redis.delete(f"password_reset_token:{previous_token}")

    await redis.setex(f"password_reset_token:{token}", ttl, str(user_id))
    await redis.setex(user_token_key, ttl, token)


async def verify_refresh_token(user_id: int, session_id: str, refresh_token: str) -> bool:
    redis = await RedisManager.get_client()
    raw_session = await redis.get(_refresh_session_key(session_id))
    if raw_session is None:
        return False

    try:
        session_data = json.loads(raw_session)
    except (TypeError, ValueError):
        return False

    return (
        session_data.get("user_id") == user_id
        and session_data.get("refresh_token") == refresh_token
    )


async def get_refresh_session_user_id(session_id: str) -> int | None:
    session = await get_refresh_session(session_id)
    if session is None:
        return None
    return session[0]


async def consume_email_verification_token(token: str) -> int | None:
    redis = await RedisManager.get_client()
    key = f"email_verify_token:{token}"
    for _ in range(8):
        async with redis.pipeline(transaction=True) as pipe:
            try:
                await pipe.watch(key)
                stored_user_id = await pipe.get(key)
                if stored_user_id is None:
                    return None
                try:
                    user_id = int(stored_user_id)
                except (TypeError, ValueError):
                    return None
                user_key = f"email_verify_user_token:{user_id}"
                await pipe.watch(user_key)
                if await pipe.get(user_key) != token:
                    return None
                pipe.multi()
                pipe.delete(key, user_key)
                await pipe.execute()
                return user_id
            except WatchError:
                continue
    raise RuntimeError("Email verification token contention")


async def consume_password_reset_token(token: str) -> int | None:
    redis = await RedisManager.get_client()
    key = f"password_reset_token:{token}"
    stored_user_id = await redis.get(key)
    if stored_user_id is None:
        return None

    try:
        user_id = int(stored_user_id)
    except (TypeError, ValueError):
        return None

    current_token = await redis.get(f"password_reset_user_token:{user_id}")
    if current_token != token:
        return None

    await redis.delete(key)
    await redis.delete(f"password_reset_user_token:{user_id}")
    return user_id


async def delete_refresh_token(user_id: int) -> None:
    redis = await RedisManager.get_client()
    session_ids = await redis.smembers(_refresh_user_sessions_key(user_id))
    if session_ids:
        session_keys = [_refresh_session_key(session_id) for session_id in session_ids]
        await redis.delete(*session_keys)
    await redis.delete(_refresh_user_sessions_key(user_id))


async def delete_account_tokens(user_id: int) -> None:
    """Remove all refresh and one-time token indexes for a deleted account."""
    await delete_refresh_token(user_id)
    redis = await RedisManager.get_client()
    await redis.delete(
        *(
            f"account_delete:{user_id}:{part}"
            for part in ("challenge", "cooldown", "budget", "failures")
        )
    )
    for prefix in ("email_verify", "password_reset"):
        key = f"{prefix}_user_token:{user_id}"
        token = await redis.get(key)
        if token:
            value = token.decode() if isinstance(token, bytes) else token
            await redis.delete(f"{prefix}_token:{value}")
        await redis.delete(key)
