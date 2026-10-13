from enum import Enum

from fastapi import status

from .error import (
    ServiceErrorCode,
    ServiceException,
    build_error_models,
    build_error_responses_from_codes,
)


class InboxErrorCode(Enum):
    NOT_FOUND = ServiceErrorCode(
        "INBOX_NOT_FOUND", "Notification not found.", status.HTTP_404_NOT_FOUND
    )

    @property
    def code(self) -> ServiceErrorCode:
        return self.value


class InboxException(ServiceException):
    def __init__(
        self,
        code: InboxErrorCode,
        message: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(code=code.code, message=message, details=details)


INBOX_ERROR_CODE_VALUES = tuple(error_code.code.error for error_code in InboxErrorCode)


InboxErrorDetail, InboxErrorResponse = build_error_models(
    detail_model_name="InboxErrorDetail",
    response_model_name="InboxErrorResponse",
    error_values=INBOX_ERROR_CODE_VALUES,
    example_error=InboxErrorCode.NOT_FOUND.code.error,
)


def inbox_error_responses(*codes: InboxErrorCode) -> dict[int, dict[str, object]]:
    return build_error_responses_from_codes(
        response_model=InboxErrorResponse,
        codes=(code.code for code in codes),
    )
