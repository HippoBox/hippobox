"""Response contracts shared by authentication dependencies and routers."""

from collections.abc import Mapping
from typing import Any

from hippobox.platform.core.error.api_key_exception import APIKeyErrorCode, api_key_error_responses
from hippobox.platform.core.error.auth_exception import AuthErrorCode, auth_error_responses


def merge_error_responses(*groups: Mapping[int, dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Preserve alternative domain models when errors share a status code."""
    result: dict[int, dict[str, Any]] = {}
    for group in groups:
        for code, entry in group.items():
            if code not in result:
                result[code] = dict(entry)
                continue
            result[code] = {
                "description": result[code]["description"],
                "model": result[code]["model"] | entry["model"],
            }
    return result


def current_user_error_responses(
    *domain_responses: Mapping[int, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    return merge_error_responses(
        auth_error_responses(
            AuthErrorCode.INVALID_TOKEN,
            AuthErrorCode.USER_NOT_FOUND,
            AuthErrorCode.INSUFFICIENT_ROLE,
        ),
        api_key_error_responses(
            APIKeyErrorCode.API_KEY_INVALID, APIKeyErrorCode.API_KEY_USER_MISMATCH
        ),
        *domain_responses,
    )
