from enum import Enum
from fastapi import status

from hippobox.errors.service import ServiceErrorCode, ServiceException


class AuthErrorCode(Enum):
    USER_NOT_FOUND = ServiceErrorCode(
        "USER_NOT_FOUND",
        "User not found",
        status.HTTP_404_NOT_FOUND,
    )

    USER_ALREADY_EXISTS = ServiceErrorCode(
        "USER_ALREADY_EXISTS",
        "User with this email already exists",
        status.HTTP_409_CONFLICT,
    )

    PASSWORD_MISMATCH = ServiceErrorCode(
        "PASSWORD_MISMATCH",
        "Incorrect password",
        status.HTTP_401_UNAUTHORIZED,
    )

    CREATE_FAILED = ServiceErrorCode(
        "CREATE_FAILED",
        "Failed to create user",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    @property
    def code(self) -> ServiceErrorCode:
        return self.value


class AuthException(ServiceException):
    def __init__(self, code: AuthErrorCode, message: str | None = None):
        super().__init__(
            code=code.code,
            message=message or code.code.default_message,
        )
