from enum import Enum

from fastapi import status

from .error import (
    ServiceErrorCode,
    ServiceException,
    build_error_models,
    build_error_responses_from_codes,
)


class AdminErrorCode(Enum):
    DEMO_DISABLED = ServiceErrorCode(
        "ADMIN_DEMO_DISABLED", "Demo is not available.", status.HTTP_404_NOT_FOUND
    )
    DEMO_FAILED = ServiceErrorCode(
        "ADMIN_DEMO_FAILED", "Unable to load demo data.", status.HTTP_503_SERVICE_UNAVAILABLE
    )

    STATUS_FAILED = ServiceErrorCode(
        "ADMIN_STATUS_FAILED",
        "Unable to inspect server status.",
        status.HTTP_503_SERVICE_UNAVAILABLE,
    )

    @property
    def code(self) -> ServiceErrorCode:
        return self.value


class AdminException(ServiceException):
    def __init__(
        self,
        code: AdminErrorCode,
        message: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(code=code.code, message=message, details=details)


ADMIN_ERROR_CODE_VALUES = tuple(error_code.code.error for error_code in AdminErrorCode)


AdminErrorDetail, AdminErrorResponse = build_error_models(
    detail_model_name="AdminErrorDetail",
    response_model_name="AdminErrorResponse",
    error_values=ADMIN_ERROR_CODE_VALUES,
    example_error=AdminErrorCode.STATUS_FAILED.code.error,
)


def admin_error_responses(*codes: AdminErrorCode) -> dict[int, dict[str, object]]:
    return build_error_responses_from_codes(
        response_model=AdminErrorResponse,
        codes=(code.code for code in codes),
    )
