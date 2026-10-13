from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field, create_model


@dataclass(frozen=True)
class ServiceErrorCode:
    error: str
    default_message: str
    status_code: int


class ServiceException(Exception):
    def __init__(
        self,
        code: ServiceErrorCode,
        message: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(message or code.default_message)
        self.code = code
        self.message = message or code.default_message
        self.details = details


class ErrorDetail(BaseModel):
    error: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    detail: ErrorDetail


def build_error_models(
    *,
    detail_model_name: str,
    response_model_name: str,
    error_values: Iterable[str],
    example_error: str,
) -> tuple[type[ErrorDetail], type[ErrorResponse]]:
    normalized_values = list(dict.fromkeys(error_values))
    detail_model = create_model(
        detail_model_name,
        __base__=ErrorDetail,
        error=(
            str,
            Field(
                json_schema_extra={
                    "enum": normalized_values,
                    "example": example_error,
                }
            ),
        ),
    )
    response_model = create_model(
        response_model_name,
        __base__=ErrorResponse,
        detail=(detail_model, ...),
    )
    return detail_model, response_model


def build_error_example(
    code: ServiceErrorCode, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error": code.error,
        "message": code.default_message,
    }
    if details is not None:
        payload["details"] = details
    return {"detail": payload}


def build_error_response_entry(
    response_model: type[BaseModel],
    description: str,
    code: ServiceErrorCode,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "model": response_model,
        "description": description,
        "content": {
            "application/json": {
                "example": build_error_example(code, details),
            }
        },
    }


def build_error_response_models(
    response_model: type[BaseModel],
    specs: Mapping[int, tuple[str, ServiceErrorCode, dict[str, Any] | None]],
) -> dict[int, dict[str, Any]]:
    return {
        status_code: build_error_response_entry(
            response_model=response_model,
            description=description,
            code=code,
            details=details,
        )
        for status_code, (description, code, details) in specs.items()
    }


def build_error_responses_from_codes(
    *,
    response_model: type[BaseModel],
    codes: Iterable[ServiceErrorCode],
    example_details_by_error: Mapping[str, dict[str, Any]] | None = None,
) -> dict[int, dict[str, Any]]:
    details_map = example_details_by_error or {}
    specs: dict[int, tuple[str, ServiceErrorCode, dict[str, Any] | None]] = {}
    for code in codes:
        status_code = code.status_code
        if status_code in specs:
            continue
        try:
            # Python 3.13 renamed these phrases; keep the shared contract stable.
            description = {
                413: "Content Too Large",
                422: "Unprocessable Content",
            }.get(status_code) or HTTPStatus(status_code).phrase
        except ValueError:
            description = str(status_code)
        specs[status_code] = (
            description,
            code,
            details_map.get(code.error),
        )
    return build_error_response_models(
        response_model=response_model,
        specs=specs,
    )


def select_error_responses(
    response_models: Mapping[int, dict[str, Any]],
    *status_codes: int,
) -> dict[int, dict[str, Any]]:
    return {status_code: response_models[status_code] for status_code in status_codes}


def service_exception_to_http(exc: ServiceException) -> HTTPException:
    payload: dict[str, str | dict] = {
        "error": exc.code.error,
        "message": exc.message,
    }
    if exc.details is not None:
        payload["details"] = exc.details
    return HTTPException(status_code=exc.code.status_code, detail=payload)
