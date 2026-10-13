from enum import Enum

from fastapi import status

from .error import (
    ServiceErrorCode,
    ServiceException,
    build_error_models,
    build_error_responses_from_codes,
)


class AuthErrorCode(Enum):
    NAME_ALREADY_EXISTS = ServiceErrorCode(
        "NAME_ALREADY_EXISTS", "User with this name already exists.", status.HTTP_409_CONFLICT
    )

    PASSWORD_CHANGE_CODE_INVALID = ServiceErrorCode(
        "PASSWORD_CHANGE_CODE_INVALID",
        "The password change code is invalid, expired or locked.",
        status.HTTP_400_BAD_REQUEST,
    )
    PASSWORD_CHANGE_CODE_THROTTLED = ServiceErrorCode(
        "PASSWORD_CHANGE_CODE_THROTTLED",
        "Wait before requesting another password change code.",
        status.HTTP_429_TOO_MANY_REQUESTS,
    )
    PASSWORD_CHANGE_CODE_SEND_FAILED = ServiceErrorCode(
        "PASSWORD_CHANGE_CODE_SEND_FAILED",
        "Unable to queue the password change code.",
        status.HTTP_503_SERVICE_UNAVAILABLE,
    )
    PASSWORD_CHANGE_FAILED = ServiceErrorCode(
        "PASSWORD_CHANGE_FAILED",
        "Unable to change the password. Request a new code and retry.",
        status.HTTP_503_SERVICE_UNAVAILABLE,
    )
    ACCOUNT_BILLING_REVIEW_REQUIRED = ServiceErrorCode(
        "ACCOUNT_BILLING_REVIEW_REQUIRED",
        "Contact the operator to reconcile subscriptions before deleting this account.",
        status.HTTP_409_CONFLICT,
    )
    ACCOUNT_DELETE_CODE_INVALID = ServiceErrorCode(
        "ACCOUNT_DELETE_CODE_INVALID",
        "The deletion code is invalid, expired or locked. Request a new code after the cooldown.",
        status.HTTP_400_BAD_REQUEST,
    )
    ACCOUNT_DELETE_CODE_THROTTLED = ServiceErrorCode(
        "ACCOUNT_DELETE_CODE_THROTTLED",
        "Wait before requesting another deletion code.",
        status.HTTP_429_TOO_MANY_REQUESTS,
    )
    ACCOUNT_DELETE_CODE_SEND_FAILED = ServiceErrorCode(
        "ACCOUNT_DELETE_CODE_SEND_FAILED",
        "Unable to queue the deletion code. Try again later.",
        status.HTTP_503_SERVICE_UNAVAILABLE,
    )
    ACCOUNT_DELETE_FAILED = ServiceErrorCode(
        "ACCOUNT_DELETE_FAILED",
        "Failed to delete account.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    ACCOUNT_DELETE_CONFIRMATION_REQUIRED = ServiceErrorCode(
        "ACCOUNT_DELETE_CONFIRMATION_REQUIRED",
        "Enter your current email to confirm deletion.",
        status.HTTP_400_BAD_REQUEST,
    )
    LAST_ADMIN_REQUIRED = ServiceErrorCode(
        "LAST_ADMIN_REQUIRED",
        "Assign another active administrator before deleting this account.",
        status.HTTP_409_CONFLICT,
    )
    ADMIN_USERS_FAILED = ServiceErrorCode(
        "ADMIN_USERS_FAILED",
        "Failed to load the user directory.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    SIGNUP_FAILED = ServiceErrorCode(
        "SIGNUP_FAILED",
        "Failed to create the user account.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    EMAIL_ALREADY_EXISTS = ServiceErrorCode(
        "EMAIL_ALREADY_EXISTS",
        "User with this email already exists.",
        status.HTTP_409_CONFLICT,
    )
    INVALID_CREDENTIALS = ServiceErrorCode(
        "INVALID_CREDENTIALS",
        "Incorrect email or password.",
        status.HTTP_401_UNAUTHORIZED,
    )
    ACCOUNT_LOCKED = ServiceErrorCode(
        "ACCOUNT_LOCKED",
        "Account is temporarily locked.",
        status.HTTP_423_LOCKED,
    )
    EMAIL_NOT_VERIFIED = ServiceErrorCode(
        "EMAIL_NOT_VERIFIED",
        "Email verification is required.",
        status.HTTP_403_FORBIDDEN,
    )
    LOGIN_DISABLED = ServiceErrorCode(
        "LOGIN_DISABLED",
        "Login is currently disabled.",
        status.HTTP_403_FORBIDDEN,
    )
    EMAIL_DISABLED = ServiceErrorCode(
        "EMAIL_DISABLED",
        "Email-based features are disabled.",
        status.HTTP_403_FORBIDDEN,
    )
    INVALID_TOKEN = ServiceErrorCode(
        "INVALID_TOKEN",
        "Invalid refresh token.",
        status.HTTP_401_UNAUTHORIZED,
    )
    INSUFFICIENT_ROLE = ServiceErrorCode(
        "INSUFFICIENT_ROLE",
        "User does not have enough permissions.",
        status.HTTP_403_FORBIDDEN,
    )
    USER_NOT_FOUND = ServiceErrorCode(
        "USER_NOT_FOUND",
        "User not found.",
        status.HTTP_404_NOT_FOUND,
    )
    PROFILE_PHOTO_INVALID = ServiceErrorCode(
        "PROFILE_PHOTO_INVALID", "Invalid profile image.", status.HTTP_422_UNPROCESSABLE_CONTENT
    )
    PROFILE_PHOTO_TOO_LARGE = ServiceErrorCode(
        "PROFILE_PHOTO_TOO_LARGE",
        "Profile image exceeds the upload limit.",
        status.HTTP_413_CONTENT_TOO_LARGE,
    )
    PROFILE_PHOTO_UNAVAILABLE = ServiceErrorCode(
        "PROFILE_PHOTO_UNAVAILABLE",
        "Profile image storage is unavailable.",
        status.HTTP_503_SERVICE_UNAVAILABLE,
    )
    PROFILE_PHOTO_NOT_FOUND = ServiceErrorCode(
        "PROFILE_PHOTO_NOT_FOUND", "Profile image not found.", status.HTTP_404_NOT_FOUND
    )
    PROFILE_PHOTO_CONFLICT = ServiceErrorCode(
        "PROFILE_PHOTO_CONFLICT",
        "Profile image changed; refresh and try again.",
        status.HTTP_409_CONFLICT,
    )
    PROFILE_UPDATE_FAILED = ServiceErrorCode(
        "PROFILE_UPDATE_FAILED",
        "Failed to update profile.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    OAUTH_PROVIDER_NOT_ENABLED = ServiceErrorCode(
        "OAUTH_PROVIDER_NOT_ENABLED",
        "The requested OAuth provider is not enabled.",
        status.HTTP_400_BAD_REQUEST,
    )
    OAUTH_PROVIDER_CONFIG_INVALID = ServiceErrorCode(
        "OAUTH_PROVIDER_CONFIG_INVALID",
        "OAuth provider configuration is invalid.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    OAUTH_IDENTITY_CONFLICT = ServiceErrorCode(
        "OAUTH_IDENTITY_CONFLICT",
        "OAuth identity is already linked to another user.",
        status.HTTP_409_CONFLICT,
    )
    OAUTH_SIGNUP_FAILED = ServiceErrorCode(
        "OAUTH_SIGNUP_FAILED",
        "Failed to create OAuth user account.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    OAUTH_PROVIDER_REQUEST_FAILED = ServiceErrorCode(
        "OAUTH_PROVIDER_REQUEST_FAILED",
        "OAuth provider request failed.",
        status.HTTP_502_BAD_GATEWAY,
    )

    @property
    def code(self) -> ServiceErrorCode:
        return self.value


class AuthException(ServiceException):
    def __init__(
        self,
        code: AuthErrorCode,
        message: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(code=code.code, message=message, details=details)


AUTH_ERROR_CODE_VALUES = tuple(error_code.code.error for error_code in AuthErrorCode)


AuthErrorDetail, AuthErrorResponse = build_error_models(
    detail_model_name="AuthErrorDetail",
    response_model_name="AuthErrorResponse",
    error_values=AUTH_ERROR_CODE_VALUES,
    example_error=AuthErrorCode.INVALID_TOKEN.code.error,
)


AUTH_ERROR_EXAMPLE_DETAILS: dict[AuthErrorCode, dict[str, object]] = {
    AuthErrorCode.ACCOUNT_LOCKED: {"remaining_seconds": 120},
}


def auth_error_responses(*codes: AuthErrorCode) -> dict[int, dict[str, object]]:
    return build_error_responses_from_codes(
        response_model=AuthErrorResponse,
        codes=(code.code for code in codes),
        example_details_by_error={
            code.code.error: details for code, details in AUTH_ERROR_EXAMPLE_DETAILS.items()
        },
    )
