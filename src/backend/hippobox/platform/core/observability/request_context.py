from contextvars import ContextVar, Token
from uuid import uuid4

from fastapi import Request, Response
from opentelemetry import trace

REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_HEADER = "X-Trace-ID"
TRACEPARENT_HEADER = "traceparent"

_REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="")
_TRACE_ID: ContextVar[str] = ContextVar("trace_id", default="")


def _clean_header_value(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def _generate_request_id() -> str:
    return str(uuid4())


def _generate_trace_id() -> str:
    return uuid4().hex


def _extract_traceparent_trace_id(traceparent: str | None) -> str:
    value = _clean_header_value(traceparent)
    if not value:
        return ""

    parts = value.split("-")
    if len(parts) < 4:
        return ""

    trace_id = parts[1].strip().lower()
    if len(trace_id) != 32:
        return ""
    if trace_id == "0" * 32:
        return ""
    if any(char not in "0123456789abcdef" for char in trace_id):
        return ""
    return trace_id


def resolve_request_id(request: Request) -> str:
    return _clean_header_value(request.headers.get(REQUEST_ID_HEADER)) or _generate_request_id()


def _active_trace_id() -> str:
    context = trace.get_current_span().get_span_context()
    # Unsampled spans still have a valid correlation ID.
    return trace.format_trace_id(context.trace_id) if context.is_valid else ""


def resolve_trace_id(request: Request) -> str:
    return (
        _active_trace_id()
        or _extract_traceparent_trace_id(request.headers.get(TRACEPARENT_HEADER))
        or _clean_header_value(request.headers.get(TRACE_ID_HEADER))
        or _generate_trace_id()
    )


def set_request_context(*, request_id: str, trace_id: str) -> tuple[Token[str], Token[str]]:
    return (
        _REQUEST_ID.set(request_id),
        _TRACE_ID.set(trace_id),
    )


def reset_request_context(tokens: tuple[Token[str], Token[str]]) -> None:
    request_id_token, trace_id_token = tokens
    _REQUEST_ID.reset(request_id_token)
    _TRACE_ID.reset(trace_id_token)


def get_request_id() -> str:
    return _REQUEST_ID.get()


def get_trace_id() -> str:
    return _active_trace_id() or _TRACE_ID.get()


def add_request_context_headers(
    response: Response,
    *,
    request_id: str,
    trace_id: str,
) -> None:
    response.headers[REQUEST_ID_HEADER] = request_id
    response.headers[TRACE_ID_HEADER] = trace_id
