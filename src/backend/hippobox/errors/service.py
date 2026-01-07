import logging
from enum import Enum

from fastapi import HTTPException

log = logging.getLogger("service")


class ServiceErrorCode:
    def __init__(self, code: str, default_message: str, http_status: int):
        self.code = code
        self.default_message = default_message
        self.http_status = http_status


class ServiceException(Exception):
    def __init__(self, code: ServiceErrorCode, message: str | None = None, details: dict | None = None):
        self.code = code
        self.message = str(message) if message else code.default_message
        self.details = details or {}
        super().__init__(self.message)


def exceptions_to_http(exc: ServiceException) -> HTTPException:
    details = {
        "error": exc.code.code,
        "message": exc.message,
    }
    if exc.details:
        details.update(exc.details)
    return HTTPException(
        status_code=exc.code.http_status,
        detail=details,
    )


def raise_exception_with_log(code: ServiceErrorCode | Enum, e: Exception):
    if isinstance(code, Enum):
        code = code.value

    if e:
        log.exception(f"{code.default_message}: {e}")
    else:
        log.exception(code.default_message)

    raise ServiceException(code)
