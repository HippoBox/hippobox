from enum import Enum

from fastapi import status

from hippobox.errors.service import ServiceErrorCode, ServiceException


class AuthErrorCode(Enum):
    UNKNOWN_ERROR = ServiceErrorCode(
        "UNKNOWN_ERROR",
        "An unknown error occurred",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

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

    NAME_ALREADY_EXISTS = ServiceErrorCode(
        "NAME_ALREADY_EXISTS",
        "User with this name already exists",
        status.HTTP_409_CONFLICT,
    )

    EMAIL_ALREADY_EXISTS = ServiceErrorCode(
        "EMAIL_ALREADY_EXISTS",
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

    LOGIN_FAILED = ServiceErrorCode(
        "LOGIN_FAILED",
        "Failed to login user",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    ACCOUNT_LOCKED = ServiceErrorCode(
        "ACCOUNT_LOCKED",
        "Account is locked due to too many failed login attempts",
        status.HTTP_423_LOCKED,
    )

    INVALID_EMAIL_VERIFY_TOKEN = ServiceErrorCode(
        "INVALID_EMAIL_VERIFY_TOKEN",
        "Invalid email verification token",
        status.HTTP_400_BAD_REQUEST,
    )

    INVALID_RESET_PASSWORD_TOKEN = ServiceErrorCode(
        "INVALID_RESET_PASSWORD_TOKEN",
        "Invalid password reset token",
        status.HTTP_400_BAD_REQUEST,
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
