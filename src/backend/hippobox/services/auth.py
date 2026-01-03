import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from functools import partial

from fastapi import Request

from hippobox.core.redis import RedisManager
from hippobox.core.settings import SETTINGS
from hippobox.errors.auth import AuthErrorCode, AuthException
from hippobox.errors.service import raise_exception_with_log
from hippobox.integrations.resend.emailer import send_password_reset_email, send_verification_email
from hippobox.models.auth import Auths
from hippobox.models.credential import Credentials
from hippobox.models.user import LoginForm, LoginTokenResponse, SignupForm, TokenRefreshResponse, UserResponse, Users
from hippobox.utils.security import get_password_hash, verify_password
from hippobox.utils.token import (
    create_access_token,
    create_refresh_token,
    delete_refresh_token,
    store_refresh_token,
    verify_refresh_token,
)

log = logging.getLogger("auth")


class AuthService:
    def __init__(self):
        self.LOGIN_FAILED_LIMIT = SETTINGS.LOGIN_FAILED_LIMIT
        self.LOGIN_LOCKED_MINUTES = SETTINGS.LOGIN_LOCKED_MINUTES
        self.ACCESS_TOKEN_EXPIRE_MINUTES = SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES

    @staticmethod
    def _decode_token(value: str | bytes) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    async def _clear_token_set(self, redis, set_key: str, token_prefix: str):
        tokens = await redis.smembers(set_key)
        if tokens:
            for raw in tokens:
                token = self._decode_token(raw)
                await redis.delete(f"{token_prefix}:{token}")
        await redis.delete(set_key)

    async def _remove_token_from_set(self, redis, set_key: str, token: str, token_prefix: str):
        await redis.delete(f"{token_prefix}:{token}")
        await redis.srem(set_key, token)
        if await redis.scard(set_key) == 0:
            await redis.delete(set_key)

    async def _hash_password(self, password: str) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, get_password_hash, password)

    async def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(verify_password, plain_password, hashed_password))

    # -------------------------------------------
    # Signup
    # -------------------------------------------
    async def signup(self, form: SignupForm) -> UserResponse:
        try:
            hashed_password = await self._hash_password(form.password)
            user_data = form.model_dump()

            if "password" in user_data:
                del user_data["password"]

            user = await Users.create(user_data)
            await Credentials.create(user.id, hashed_password)
            await Auths.create(user.id, "email", user.email)

        except AuthException as e:
            raise e

        except Exception as e:
            raise_exception_with_log(AuthErrorCode.CREATE_FAILED, e)

        await self._create_email_verification_token(user.id, user.email, user.name)

        return UserResponse.model_validate(user.model_dump())

    # -------------------------------------------
    # Login
    # -------------------------------------------
    async def login(self, form: LoginForm, request: Request) -> LoginTokenResponse:
        try:
            user = await Users.get_entity_by_email(form.email)
        except Exception as e:
            raise_exception_with_log(AuthErrorCode.LOGIN_FAILED, e)

        if user is None:
            raise AuthException(AuthErrorCode.INVALID_CREDENTIALS)

        await self._check_login_limit(user.id)

        credential = await Credentials.get_by_user_id(user.id)
        if credential is None or not credential.is_active:
            raise AuthException(AuthErrorCode.INVALID_CREDENTIALS)

        is_valid = await self._verify_password(form.password, credential.password_hash)

        if not is_valid:
            await self._increase_login_fail_count(user.id)
            raise AuthException(AuthErrorCode.INVALID_CREDENTIALS)

        await self._reset_login_fail_count(user.id)

        if not user.is_verified:
            raise AuthException(AuthErrorCode.EMAIL_NOT_VERIFIED)

        try:
            client_host = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            await Auths.update_last_login(user.id, datetime.now(timezone.utc), client_host, user_agent)
        except Exception as e:
            log.warning(f"Failed to update last_login_at for user {user.id}: {e}")
            raise_exception_with_log(AuthErrorCode.LOGIN_FAILED, e)

        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role},
            expires_delta=timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = create_refresh_token()

        await store_refresh_token(user.id, refresh_token)

        return LoginTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    # -------------------------------------------
    # Logout
    # -------------------------------------------
    async def logout(self, user_id: int):
        await delete_refresh_token(user_id)

    # -------------------------------------------
    # Refresh Token
    # -------------------------------------------
    async def refresh_access_token(self, refresh_token: str, user_id: int) -> TokenRefreshResponse:
        is_valid = await verify_refresh_token(user_id, refresh_token)

        if not is_valid:
            raise AuthException(AuthErrorCode.INVALID__AUTH_TOKEN)

        user = await Users.get(user_id)
        if not user:
            raise AuthException(AuthErrorCode.USER_NOT_FOUND)

        new_access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role},
            expires_delta=timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        new_refresh_token = create_refresh_token()

        await store_refresh_token(user.id, new_refresh_token)

        return TokenRefreshResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
        )

    # -------------------------------------------
    # Email Verification
    # -------------------------------------------
    async def _create_email_verification_token(self, user_id: int, email: str, name: str | None = None):
        try:
            redis = await RedisManager.get_client()
            token = str(uuid.uuid4())
            set_key = f"email_verify_user:{user_id}"

            try:
                await self._clear_token_set(redis, set_key, "email_verify")
            except Exception as exc:
                log.warning("Failed to clear prior verification tokens for %s: %s", email, exc)

            await redis.setex(f"email_verify:{token}", timedelta(minutes=10), user_id)
            await redis.sadd(set_key, token)
            await redis.expire(set_key, timedelta(minutes=10))
            try:
                await send_verification_email(email=email, name=name, token=token)
            except Exception as exc:
                log.warning("Failed to send verification email to %s: %s", email, exc)

            log.info("Email verification token created for %s", email)
        except Exception as e:
            log.error(f"Failed to create email verification token: {e}")

    async def verify_email(self, token: str) -> UserResponse:
        redis = await RedisManager.get_client()
        user_id = await redis.get(f"email_verify:{token}")

        if user_id is None:
            raise AuthException(AuthErrorCode.INVALID_EMAIL_VERIFY_TOKEN)

        try:
            numeric_user_id = int(user_id)
            updated = await Users.update(numeric_user_id, {"is_verified": True})
        except Exception as e:
            raise_exception_with_log(AuthErrorCode.UNKNOWN_ERROR, e)

        try:
            await self._remove_token_from_set(redis, f"email_verify_user:{numeric_user_id}", token, "email_verify")
        except Exception as exc:
            log.warning("Failed to clear verification token for %s: %s", user_id, exc)

        if updated is None:
            raise AuthException(AuthErrorCode.INVALID_EMAIL_VERIFY_TOKEN)

        return UserResponse.model_validate(updated.model_dump())

    async def resend_verification_email(self, email: str):
        try:
            user = await Users.get_entity_by_email(email)
        except Exception as e:
            raise_exception_with_log(AuthErrorCode.UNKNOWN_ERROR, e)

        if user is None or user.is_verified:
            return

        await self._create_email_verification_token(user.id, user.email, user.name)

    # -------------------------------------------
    # Password Reset
    # -------------------------------------------
    async def request_password_reset(self, email: str):
        try:
            user = await Users.get_entity_by_email(email)
        except Exception as e:
            raise_exception_with_log(AuthErrorCode.UNKNOWN_ERROR, e)

        if user is None:
            raise AuthException(AuthErrorCode.USER_NOT_FOUND)

        redis = await RedisManager.get_client()
        token = str(uuid.uuid4())
        set_key = f"reset_pw_user:{user.id}"

        try:
            await self._clear_token_set(redis, set_key, "reset_pw")
        except Exception as exc:
            log.warning("Failed to clear prior reset tokens for %s: %s", email, exc)

        await redis.setex(f"reset_pw:{token}", timedelta(minutes=10), user.id)
        await redis.sadd(set_key, token)
        await redis.expire(set_key, timedelta(minutes=10))
        try:
            await send_password_reset_email(email=email, name=user.name, token=token)
        except Exception as exc:
            log.warning("Failed to send password reset email to %s: %s", email, exc)

        log.info("Password reset token created for %s", email)

    async def reset_password(self, token: str, new_password: str):
        redis = await RedisManager.get_client()
        user_id = await redis.get(f"reset_pw:{token}")

        if user_id is None:
            raise AuthException(AuthErrorCode.INVALID_RESET_PASSWORD_TOKEN)

        hashed_password = await self._hash_password(new_password)
        try:
            numeric_user_id = int(user_id)
            updated = await Credentials.update(
                numeric_user_id,
                {"password_hash": hashed_password, "password_changed_at": datetime.now(timezone.utc)},
            )
        except Exception as e:
            raise_exception_with_log(AuthErrorCode.UNKNOWN_ERROR, e)

        try:
            await self._remove_token_from_set(redis, f"reset_pw_user:{numeric_user_id}", token, "reset_pw")
        except Exception as exc:
            log.warning("Failed to clear reset token for %s: %s", user_id, exc)

        if updated is None:
            raise AuthException(AuthErrorCode.INVALID_RESET_PASSWORD_TOKEN)

    # -------------------------------------------
    # Login Attempt Rate Limiting (Redis)
    # -------------------------------------------
    async def _check_login_limit(self, user_id: int):
        try:
            redis = await RedisManager.get_client()
            fails = await redis.get(f"login_fail:{user_id}")

            if fails and int(fails) >= self.LOGIN_FAILED_LIMIT:
                raise AuthException(AuthErrorCode.ACCOUNT_LOCKED)

        except Exception as e:
            log.error(f"Redis login-limit check failed: {e}")
            raise AuthException(AuthErrorCode.UNKNOWN_ERROR, e)

    async def _increase_login_fail_count(self, user_id: int):
        try:
            redis = await RedisManager.get_client()
            key = f"login_fail:{user_id}"

            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, timedelta(minutes=self.LOGIN_LOCKED_MINUTES))

        except Exception as e:
            log.error(f"Redis login-fail increase failed: {e}")

    async def _reset_login_fail_count(self, user_id: int):
        try:
            redis = await RedisManager.get_client()
            await redis.delete(f"login_fail:{user_id}")
        except Exception as e:
            log.error(f"Redis login-fail reset failed: {e}")


def get_auth_service(request: Request) -> AuthService:
    return AuthService()
