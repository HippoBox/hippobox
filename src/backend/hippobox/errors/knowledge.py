from enum import Enum

from fastapi import status

from hippobox.errors.service import ServiceErrorCode, ServiceException


class KnowledgeErrorCode(Enum):
    NOT_FOUND = ServiceErrorCode(
        "NOT_FOUND",
        "Knowledge not found",
        status.HTTP_404_NOT_FOUND,
    )

    GET_FAILED = ServiceErrorCode(
        "GET_FAILED",
        "Failed to retrieve knowledge",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    CREATE_FAILED = ServiceErrorCode(
        "CREATE_FAILED",
        "Failed to create knowledge",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    TITLE_EXISTS = ServiceErrorCode(
        "TITLE_EXISTS",
        "A knowledge entry with the same title already exists.",
        status.HTTP_409_CONFLICT,
    )

    UPDATE_FAILED = ServiceErrorCode(
        "UPDATE_FAILED",
        "Failed to update knowledge",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    DELETE_FAILED = ServiceErrorCode(
        "DELETE_FAILED",
        "Failed to delete knowledge",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    VDB_DISABLED = ServiceErrorCode(
        "VDB_DISABLED",
        "Vector search is disabled",
        status.HTTP_503_SERVICE_UNAVAILABLE,
    )

    @property
    def code(self) -> ServiceErrorCode:
        return self.value


class KnowledgeException(ServiceException):
    def __init__(self, code: KnowledgeErrorCode, message: str | None = None):
        super().__init__(code=code.code, message=message or code.code.default_message)
