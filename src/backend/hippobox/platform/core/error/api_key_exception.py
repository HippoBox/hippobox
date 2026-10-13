from enum import Enum

from fastapi import status

from .error import (
    ServiceErrorCode,
    ServiceException,
    build_error_models,
    build_error_responses_from_codes,
)


class APIKeyErrorCode(Enum):
    API_KEY_INVALID = ServiceErrorCode(
        "API_KEY_INVALID",
        "Invalid API key.",
        status.HTTP_401_UNAUTHORIZED,
    )
    API_KEY_USER_MISMATCH = ServiceErrorCode(
        "API_KEY_USER_MISMATCH",
        "API key does not belong to the authenticated user.",
        status.HTTP_403_FORBIDDEN,
    )
    API_KEY_CREATE_FAILED = ServiceErrorCode(
        "API_KEY_CREATE_FAILED",
        "Failed to create API key.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    API_KEY_NAME_ALREADY_EXISTS = ServiceErrorCode(
        "API_KEY_NAME_ALREADY_EXISTS",
        "API key name already exists.",
        status.HTTP_409_CONFLICT,
    )
    API_KEY_NOT_FOUND = ServiceErrorCode(
        "API_KEY_NOT_FOUND",
        "API key not found.",
        status.HTTP_404_NOT_FOUND,
    )
    API_KEY_UPDATE_FAILED = ServiceErrorCode(
        "API_KEY_UPDATE_FAILED",
        "Failed to update API key state.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    @property
    def code(self) -> ServiceErrorCode:
        return self.value


class APIKeyException(ServiceException):
    def __init__(
        self,
        code: APIKeyErrorCode,
        message: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(code=code.code, message=message, details=details)


API_KEY_ERROR_CODE_VALUES = tuple(error_code.code.error for error_code in APIKeyErrorCode)


APIKeyErrorDetail, APIKeyErrorResponse = build_error_models(
    detail_model_name="APIKeyErrorDetail",
    response_model_name="APIKeyErrorResponse",
    error_values=API_KEY_ERROR_CODE_VALUES,
    example_error=APIKeyErrorCode.API_KEY_NOT_FOUND.code.error,
)


def api_key_error_responses(*codes: APIKeyErrorCode) -> dict[int, dict[str, object]]:
    return build_error_responses_from_codes(
        response_model=APIKeyErrorResponse,
        codes=(code.code for code in codes),
    )
