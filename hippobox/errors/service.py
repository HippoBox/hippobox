import logging

from fastapi import HTTPException

log = logging.getLogger("service")


class ServiceErrorCode:
    def __init__(self, code: str, default_message: str, http_status: int):
        self.code = code
        self.default_message = default_message
        self.http_status = http_status


class ServiceException(Exception):
    def __init__(self, code: ServiceErrorCode, message: str | None = None):
        self.code = code
        self.message = message or code.default_message
        super().__init__(self.message)


def exceptions_to_http(exc: ServiceException) -> HTTPException:
    return HTTPException(
        status_code=exc.code.http_status,
        detail=exc.message,
    )


def raise_exception_with_log(code: ServiceErrorCode, e: Exception):
    if e:
        log.exception(f"{code.default_message}: {e}")
    else:
        log.exception(code.default_message)

    raise ServiceException(code)
