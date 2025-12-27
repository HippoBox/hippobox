from enum import Enum

from fastapi import status

from hippobox.errors.service import ServiceErrorCode, ServiceException


class ApiKeyErrorCode(Enum):
    NOT_FOUND = ServiceErrorCode(
        "NOT_FOUND",
        "The requested API Key was not found.",
        status.HTTP_404_NOT_FOUND,
    )

    CREATE_FAILED = ServiceErrorCode(
        "CREATE_FAILED",
        "Failed to create API Key.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    UPDATE_FAILED = ServiceErrorCode(
        "UPDATE_FAILED",
        "Failed to update API Key",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    DELETE_FAILED = ServiceErrorCode(
        "DELETE_FAILED",
        "Failed to delete API Key",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


class APIKeyException(ServiceException):
    def __init__(self, code: ApiKeyErrorCode, message: str | None = None):
        super().__init__(code=code.code, message=message or code.code.default_message)
