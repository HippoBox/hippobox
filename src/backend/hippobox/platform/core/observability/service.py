"""Observation of async service operations without inspecting application payloads."""

import asyncio
from collections.abc import Callable, Coroutine
from contextlib import nullcontext
from functools import wraps
from inspect import iscoroutinefunction
from time import perf_counter
from typing import Any, ParamSpec, TypeVar

from opentelemetry import trace
from opentelemetry.trace import StatusCode

from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.error.error import ServiceException
from hippobox.platform.core.observability.logging import get_logger

P = ParamSpec("P")
R = TypeVar("R")
logger = get_logger("hippobox.platform.service.observation")


def observe_service(
    operation: str,
) -> Callable[[Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]]:
    """Log one completion and optionally trace an async service method.

    Operation names must be static identifiers, never request-derived values.
    Arguments, results, exception messages, and stack traces are not captured.
    """

    def decorate(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
        if not iscoroutinefunction(func):
            raise TypeError(
                "observe_service supports async functions, not sync functions or streams."
            )

        @wraps(func)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            context = (
                trace.get_tracer(__name__).start_as_current_span(
                    operation, record_exception=False, set_status_on_exception=False
                )
                if SETTINGS.TRACING_ENABLED
                else nullcontext(trace.INVALID_SPAN)
            )
            with context as span:
                started = perf_counter()
                outcome = "aborted"
                error_code = ""
                try:
                    result = await func(*args, **kwargs)
                    outcome = "success"
                    return result
                except asyncio.CancelledError:
                    outcome = "cancelled"
                    raise
                except Exception as error:
                    outcome = "error"
                    error_code = (
                        error.code.error
                        if isinstance(error, ServiceException)
                        else "INTERNAL_ERROR"
                    )
                    span.set_attribute("hippobox.platform.error_code", error_code)
                    span.set_status(StatusCode.ERROR)
                    raise
                finally:
                    span.set_attribute("hippobox.platform.outcome", outcome)
                    logger.debug(
                        "Service operation completed (operation=%s, outcome=%s, duration_ms=%.3f, code=%s).",
                        operation,
                        outcome,
                        (perf_counter() - started) * 1000,
                        error_code or "-",
                    )

        return wrapped

    return decorate
