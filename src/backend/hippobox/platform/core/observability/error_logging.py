"""Log severity policy for exceptions reaching the global handlers."""

import logging

from fastapi import status

from hippobox.platform.core.error import APIKeyErrorCode, AuthErrorCode

_SECURITY_ERROR_CODES = frozenset(
    code.code.error
    for code in (
        AuthErrorCode.INVALID_CREDENTIALS,
        AuthErrorCode.INVALID_TOKEN,
        AuthErrorCode.ACCOUNT_LOCKED,
        AuthErrorCode.INSUFFICIENT_ROLE,
        AuthErrorCode.OAUTH_IDENTITY_CONFLICT,
        APIKeyErrorCode.API_KEY_INVALID,
        APIKeyErrorCode.API_KEY_USER_MISMATCH,
    )
)


def exception_log_level(status_code: int, *, error_code: str | None = None) -> int:
    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        return logging.ERROR
    if error_code in _SECURITY_ERROR_CODES or status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return logging.WARNING
    if error_code is None and status_code in {
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    }:
        return logging.WARNING
    if status.HTTP_400_BAD_REQUEST <= status_code < status.HTTP_500_INTERNAL_SERVER_ERROR:
        return logging.INFO
    return logging.ERROR
