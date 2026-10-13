from enum import Enum

from fastapi import status

from .error import (
    ServiceErrorCode,
    ServiceException,
    build_error_models,
    build_error_responses_from_codes,
)


class InquiryErrorCode(Enum):
    NOT_FOUND = ServiceErrorCode(
        "INQUIRY_NOT_FOUND", "Inquiry not found.", status.HTTP_404_NOT_FOUND
    )

    CLOSED = ServiceErrorCode("INQUIRY_CLOSED", "This inquiry is closed.", status.HTTP_409_CONFLICT)
    THREAD_FULL = ServiceErrorCode(
        "INQUIRY_THREAD_FULL", "Start a new inquiry to continue.", status.HTTP_409_CONFLICT
    )

    @property
    def code(self) -> ServiceErrorCode:
        return self.value


class InquiryException(ServiceException):
    def __init__(
        self,
        code: InquiryErrorCode,
        message: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(code=code.code, message=message, details=details)


INQUIRY_ERROR_CODE_VALUES = tuple(error_code.code.error for error_code in InquiryErrorCode)


InquiryErrorDetail, InquiryErrorResponse = build_error_models(
    detail_model_name="InquiryErrorDetail",
    response_model_name="InquiryErrorResponse",
    error_values=INQUIRY_ERROR_CODE_VALUES,
    example_error=InquiryErrorCode.NOT_FOUND.code.error,
)


def inquiry_error_responses(*codes: InquiryErrorCode) -> dict[int, dict[str, object]]:
    return build_error_responses_from_codes(
        response_model=InquiryErrorResponse,
        codes=(code.code for code in codes),
    )
