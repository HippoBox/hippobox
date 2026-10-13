"""Log correlation for queued work; does not create or propagate OTel spans."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_TASK_CONTEXT: ContextVar[tuple[str, str]] = ContextVar("task_log_context", default=("", ""))


def get_task_context() -> tuple[str, str]:
    return _TASK_CONTEXT.get()


@contextmanager
def task_log_context(*, task_id: str, trace_id: str) -> Iterator[None]:
    token = _TASK_CONTEXT.set((task_id, trace_id))
    try:
        yield
    finally:
        _TASK_CONTEXT.reset(token)
