from enum import Enum

from fastapi import status

from hippobox.errors.service import ServiceErrorCode, ServiceException


class TopicErrorCode(Enum):
    NOT_FOUND = ServiceErrorCode(
        "NOT_FOUND",
        "The requested topic was not found.",
        status.HTTP_404_NOT_FOUND,
    )

    CREATE_FAILED = ServiceErrorCode(
        "CREATE_FAILED",
        "Failed to create topic.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    UPDATE_FAILED = ServiceErrorCode(
        "UPDATE_FAILED",
        "Failed to update topic.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    DELETE_FAILED = ServiceErrorCode(
        "DELETE_FAILED",
        "Failed to delete topic.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    NAME_EXISTS = ServiceErrorCode(
        "NAME_EXISTS",
        "A topic with the same name already exists.",
        status.HTTP_409_CONFLICT,
    )

    INVALID_NAME = ServiceErrorCode(
        "INVALID_NAME",
        "Topic name is required.",
        status.HTTP_400_BAD_REQUEST,
    )

    DELETE_DEFAULT = ServiceErrorCode(
        "DEFAULT_TOPIC",
        "The default topic cannot be deleted.",
        status.HTTP_400_BAD_REQUEST,
    )


class TopicException(ServiceException):
    def __init__(self, code: TopicErrorCode, message: str | None = None):
        super().__init__(code=code.value, message=message or code.value.default_message)
