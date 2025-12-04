import logging
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.hash import bcrypt

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

        return UserResponse.model_validate(user.model_dump())

    # -------------------------------------------
    # Login
    # -------------------------------------------
    async def login(self, form: LoginForm) -> dict:
        user = await Users.get_entity_by_email(form.email)

        if user is None:
            raise AuthException(AuthErrorCode.USER_NOT_FOUND)

        if not bcrypt.verify(form.password, user.password_hash):
            raise AuthException(AuthErrorCode.PASSWORD_MISMATCH)

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
            "user": UserResponse.model_validate(user),
        }
