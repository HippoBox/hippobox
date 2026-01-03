from enum import Enum

from fastapi import status

from hippobox.errors.service import ServiceErrorCode, ServiceException


class AdminErrorCode(Enum):
    LIST_USERS_FAILED = ServiceErrorCode(
        "LIST_USERS_FAILED",
        "Failed to retrieve user list",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    DELETE_USER_FAILED = ServiceErrorCode(
        "DELETE_USER_FAILED",
        "Failed to delete user",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    USER_NOT_FOUND = ServiceErrorCode(
        "USER_NOT_FOUND",
        "User not found",
        status.HTTP_404_NOT_FOUND,
    )

    @property
    def code(self) -> ServiceErrorCode:
        return self.value


class AdminException(ServiceException):
    def __init__(self, code: AdminErrorCode, message: str | None = None):
        super().__init__(code=code.code, message=message or code.code.default_message)
