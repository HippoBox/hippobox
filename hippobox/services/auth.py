import logging
import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.hash import bcrypt

from hippobox.core.redis import RedisManager
from hippobox.core.settings import SETTINGS
from hippobox.errors.auth import AuthErrorCode, AuthException
from hippobox.errors.service import raise_exception_with_log
from hippobox.models.user import LoginForm, SignupForm, UserResponse, Users

log = logging.getLogger("auth")


class AuthService:
    def __init__(self):
        self.SECRET_KEY = SETTINGS.SECRET_KEY
        self.ALGORITHM = SETTINGS.ALGORITHM
        self.ACCESS_TOKEN_EXPIRE_MINUTES = SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES

    # -------------------------------------------
    # Signup
    # -------------------------------------------
    async def signup(self, form: SignupForm) -> UserResponse:
        try:
            user = await Users.create(form)
        except Exception as e:
            raise_exception_with_log(AuthErrorCode.CREATE_FAILED, e)

        if user is None:
            raise AuthException(AuthErrorCode.USER_ALREADY_EXISTS)

        await self._create_email_verification_token(user.id, user.email)

        return UserResponse.model_validate(user.model_dump())

    # -------------------------------------------
    # Login
    # -------------------------------------------
    async def login(self, form: LoginForm) -> dict:
        user = await Users.get_entity_by_email(form.email)
        if user is None:
            raise AuthException(AuthErrorCode.USER_NOT_FOUND)

        await self._check_login_limit(user.id)

        if not bcrypt.verify(form.password, user.password_hash):
            await self._increase_login_fail_count(user.id)
            raise AuthException(AuthErrorCode.PASSWORD_MISMATCH)

        await self._reset_login_fail_count(user.id)
        await Users.update(user.id, {"last_login_at": datetime.now(timezone.utc)})

        expire = datetime.now(timezone.utc) + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "sub": str(user.id),
            "email": user.email,
            "exp": expire,
        }

        token = jwt.encode(payload, self.SECRET_KEY, algorithm=self.ALGORITHM)

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(user.model_dump()),
        }

    # -------------------------------------------
    # Email Verification
    # -------------------------------------------
    async def _create_email_verification_token(self, user_id: int, email: str):
        try:
            redis = await RedisManager.get_client()
            token = str(uuid.uuid4())

            await redis.setex(f"email_verify:{token}", timedelta(minutes=10), user_id)

            log.info(f"Email verification token created for {email}: {token}")
        except Exception as e:
            log.error(f"Failed to create email verification token: {e}")

    async def verify_email(self, token: str) -> UserResponse:
        try:
            redis = await RedisManager.get_client()
            user_id = await redis.get(f"email_verify:{token}")

            if user_id is None:
                raise AuthException(AuthErrorCode.INVALID_EMAIL_VERIFY_TOKEN)

            updated = await Users.update(int(user_id), {"is_verified": True})
            await redis.delete(f"email_verify:{token}")

            return UserResponse.model_validate(updated.model_dump())

        except AuthException:
            raise
        except Exception as e:
            raise_exception_with_log(AuthErrorCode.UNKNOWN_ERROR, e)

    # -------------------------------------------
    # Password Reset
    # -------------------------------------------
    async def request_password_reset(self, email: str):
        user = await Users.get_entity_by_email(email)
        if user is None:
            raise AuthException(AuthErrorCode.USER_NOT_FOUND)

        try:
            redis = await RedisManager.get_client()
            token = str(uuid.uuid4())

            await redis.setex(f"reset_pw:{token}", timedelta(minutes=10), user.id)
            log.info(f"Password reset token created for {email}: {token}")

        except Exception as e:
            raise_exception_with_log(AuthErrorCode.UNKNOWN_ERROR, e)

    async def reset_password(self, token: str, new_password: str):
        try:
            redis = await RedisManager.get_client()
            user_id = await redis.get(f"reset_pw:{token}")

            if user_id is None:
                raise AuthException(AuthErrorCode.INVALID_RESET_PASSWORD_TOKEN)

            await Users.update(int(user_id), {"password": new_password})
            await redis.delete(f"reset_pw:{token}")

        except AuthException:
            raise
        except Exception as e:
            raise_exception_with_log(AuthErrorCode.UNKNOWN_ERROR, e)

    # -------------------------------------------
    # Login Attempt Rate Limiting (Redis)
    # -------------------------------------------
    async def _check_login_limit(self, user_id: int):
        try:
            redis = await RedisManager.get_client()
            fails = await redis.get(f"login_fail:{user_id}")

            if fails and int(fails) >= 5:
                raise AuthException(AuthErrorCode.ACCOUNT_LOCKED)

        except Exception as e:
            log.error(f"Redis login-limit check failed: {e}")

    async def _increase_login_fail_count(self, user_id: int):
        try:
            redis = await RedisManager.get_client()
            key = f"login_fail:{user_id}"

            if not await redis.exists(key):
                await redis.setex(key, timedelta(minutes=5), 1)
            else:
                await redis.incr(key)

        except Exception as e:
            log.error(f"Redis login-fail increase failed: {e}")

    async def _reset_login_fail_count(self, user_id: int):
        try:
            redis = await RedisManager.get_client()
            await redis.delete(f"login_fail:{user_id}")
        except Exception as e:
            log.error(f"Redis login-fail reset failed: {e}")
