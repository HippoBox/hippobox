import logging
from copy import copy
from http import HTTPStatus

from rich.console import Console
from rich.style import Style
from uvicorn.logging import AccessFormatter, DefaultFormatter

from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.observability.request_context import get_request_id, get_trace_id
from hippobox.platform.core.observability.task_context import get_task_context

APP_LOGGER_NAME = "uvicorn.app"
UVICORN_ERROR_LOGGER_NAME = "uvicorn.error"
LOG_FORMAT_CONSOLE = "%(asctime)s  %(level_label)s %(source)s%(message)s%(request_context)s"
LOG_DATE_FORMAT = "%H:%M:%S"
_TIME_STYLE = Style(color="color(245)")
_PATH_STYLE = Style(color="color(75)")
_METHOD_STYLES = {
    "GET": Style(color="green"),
    "POST": Style(color="cyan"),
    "PUT": Style(color="yellow"),
    "PATCH": Style(color="magenta"),
    "DELETE": Style(color="red"),
    "HEAD": Style(color="blue"),
    "OPTIONS": Style(color="bright_black"),
}
# Separate severity, message and HTTP-status palettes from HTTP method colors.
_LEVEL_STYLES = {
    5: Style(color="color(110)", bold=True),  # Uvicorn TRACE
    logging.DEBUG: Style(color="color(180)", bold=True),
    logging.INFO: Style(color="color(141)", bold=True),
    logging.WARNING: Style(color="color(214)", bold=True),
    logging.ERROR: Style(color="color(205)", bold=True),
    logging.CRITICAL: Style(color="color(231)", bgcolor="color(52)", bold=True),
}
_MESSAGE_STYLES = {
    5: Style(color="color(152)"),
    logging.DEBUG: Style(color="color(187)"),
    logging.INFO: Style(color="color(183)"),
    logging.WARNING: Style(color="color(223)"),
    logging.ERROR: Style(color="color(217)"),
    logging.CRITICAL: Style(color="color(210)", bold=True),
}
_STATUS_STYLES = {
    1: Style(color="color(250)"),
    2: Style(color="color(84)"),
    3: Style(color="color(222)"),
    4: Style(color="color(209)"),
    5: Style(color="color(196)", bold=True),
}
_ORIGINAL_LOG_RECORD_FACTORY = logging.getLogRecordFactory()
_REQUEST_CONTEXT_RECORD_FACTORY_CONFIGURED = False
_REQUEST_CONTEXT_LOG_ENABLED = SETTINGS.LOG_LEVEL.upper() == "DEBUG"


def _build_logger_name(name: str) -> str:
    if name == UVICORN_ERROR_LOGGER_NAME:
        return "uvicorn.server"

    normalized = name
    if normalized.startswith("uvicorn.app."):
        normalized = normalized.removeprefix("uvicorn.app.")
    if normalized.startswith("hippobox.platform."):
        normalized = normalized.removeprefix("hippobox.platform.")
    if normalized.startswith("router."):
        normalized = "routers." + normalized.removeprefix("router.")
    if normalized.startswith("service."):
        normalized = "services." + normalized.removeprefix("service.")
    return normalized


def _build_request_context_field(request_id: str, trace_id: str) -> str:
    if not request_id and not trace_id:
        return ""
    return f" request_id={request_id or '-'} trace_id={trace_id or '-'}"


def _should_emit_request_context(*, levelno: int) -> bool:
    if _REQUEST_CONTEXT_LOG_ENABLED:
        return True
    # In non-debug environments, include request/trace ids for error tracking.
    return levelno >= logging.ERROR


def _resolve_request_context_field(*, levelno: int, request_id: str, trace_id: str) -> str:
    if not _should_emit_request_context(levelno=levelno):
        return ""
    return _build_request_context_field(request_id, trace_id)


def _populate_log_context(record: logging.LogRecord) -> None:
    task_id, task_trace_id = get_task_context()
    record.logger_name = _build_logger_name(record.name)
    # A queued task has its own log context, not the worker caller's HTTP context.
    record.request_id = "" if task_id else get_request_id()
    record.trace_id = task_trace_id if task_id else get_trace_id()
    record.task_id = task_id
    if task_id:
        # Include IDs even for INFO/WARNING task logs; a missing ID stays explicit.
        record.request_context = f" task_id={task_id} trace_id={task_trace_id or '-'}"
    else:
        record.request_context = _resolve_request_context_field(
            levelno=record.levelno,
            request_id=record.request_id,
            trace_id=record.trace_id,
        )


def _request_context_log_record_factory(*args, **kwargs) -> logging.LogRecord:
    record = _ORIGINAL_LOG_RECORD_FACTORY(*args, **kwargs)
    _populate_log_context(record)
    return record


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        _populate_log_context(record)
        return True


class MetricsAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Uvicorn access args: client, method, full path, HTTP version, status.
        args = record.args
        if record.name == "uvicorn.access" and isinstance(args, tuple) and len(args) == 5:
            path = args[2]
            if isinstance(path, str) and path.partition("?")[0] == "/metrics":
                return False
        return True


class SuccessfulPreflightConsoleFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if record.name == "uvicorn.access" and isinstance(args, tuple) and len(args) == 5:
            _, method, _, _, status_code = args
            if (
                method == "OPTIONS"
                and isinstance(status_code, int)
                and record.levelno == logging.INFO
            ):
                return not 200 <= status_code < 300
        return True


class CompactAccessFormatter(AccessFormatter):
    """Leave the original client/protocol/message intact for non-console handlers."""

    def get_status_code(self, status_code: int) -> str:
        try:
            phrase = HTTPStatus(status_code).phrase
        except ValueError:
            phrase = ""
        status_text = f"{status_code} {phrase}"
        if self.use_colors:
            return _STATUS_STYLES.get(status_code // 100, Style()).render(status_text)
        return status_text

    def formatMessage(self, record: logging.LogRecord) -> str:
        args = record.args
        if not isinstance(args, tuple) or len(args) != 5:
            return record.getMessage()
        _, method, full_path, _, status_code = args
        record_copy = copy(record)
        method_text = str(method).ljust(8)
        path_text = str(full_path).ljust(52)
        record_copy.method = method_text
        record_copy.path = path_text
        if self.use_colors:
            record_copy.asctime = _TIME_STYLE.render(record.asctime)
            record_copy.method = _METHOD_STYLES.get(str(method), Style()).render(method_text)
            record_copy.path = _PATH_STYLE.render(path_text)
        record_copy.status_code = self.get_status_code(int(status_code))
        return logging.Formatter.formatMessage(self, record_copy)


class CompactLogFormatter(DefaultFormatter):
    def formatMessage(self, record: logging.LogRecord) -> str:
        record_copy = copy(record)
        if self.use_colors:
            record_copy.asctime = _TIME_STYLE.render(record.asctime)
        level = record.levelname.ljust(8)
        record_copy.level_label = (
            _LEVEL_STYLES.get(record.levelno, Style(bold=True)).render(level)
            if self.use_colors
            else level
        )
        if self.use_colors:
            record_copy.message = _MESSAGE_STYLES.get(record.levelno, Style()).render(
                record.message
            )
        source = getattr(record, "logger_name", _build_logger_name(record.name))
        record_copy.source = (
            f"[{source}] "
            if _REQUEST_CONTEXT_LOG_ENABLED
            or record.levelno <= logging.DEBUG
            or record.levelno >= logging.ERROR
            else ""
        )
        record_copy.request_context = getattr(record, "request_context", "")
        return logging.Formatter.formatMessage(self, record_copy)


def _console_uses_colors(handler: logging.StreamHandler) -> bool:
    console = Console(file=handler.stream)
    return console.is_terminal and not console.no_color and not console.is_dumb_terminal


def get_logger(name: str | None = None) -> logging.Logger:
    if not name:
        return logging.getLogger(APP_LOGGER_NAME)
    return logging.getLogger(f"{APP_LOGGER_NAME}.{name}")


def configure_request_context_logging() -> None:
    global _REQUEST_CONTEXT_RECORD_FACTORY_CONFIGURED
    if not _REQUEST_CONTEXT_RECORD_FACTORY_CONFIGURED:
        logging.setLogRecordFactory(_request_context_log_record_factory)
        _REQUEST_CONTEXT_RECORD_FACTORY_CONFIGURED = True

    access_logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, MetricsAccessFilter) for item in access_logger.filters):
        access_logger.addFilter(MetricsAccessFilter())
    for handler in access_logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.FileHandler
        ):
            handler.setFormatter(
                CompactAccessFormatter(
                    fmt="%(asctime)s  %(method)s %(path)s %(status_code)s",
                    datefmt=LOG_DATE_FORMAT,
                    use_colors=_console_uses_colors(handler),
                )
            )
            if not any(
                isinstance(item, SuccessfulPreflightConsoleFilter) for item in handler.filters
            ):
                handler.addFilter(SuccessfulPreflightConsoleFilter())

    context_filter = RequestContextFilter()
    for logger_name in ("uvicorn.error", "uvicorn"):
        logger = logging.getLogger(logger_name)
        if not any(isinstance(item, RequestContextFilter) for item in logger.filters):
            logger.addFilter(context_filter)
        for handler in logger.handlers:
            if not any(isinstance(item, RequestContextFilter) for item in handler.filters):
                handler.addFilter(context_filter)
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                handler.setFormatter(
                    CompactLogFormatter(
                        fmt=LOG_FORMAT_CONSOLE,
                        datefmt=LOG_DATE_FORMAT,
                        use_colors=_console_uses_colors(handler),
                    )
                )


def mask_email(email: str) -> str:
    normalized = email.strip()
    if "@" not in normalized:
        return "***"

    local_part, domain = normalized.split("@", 1)
    if not local_part:
        return f"***@{domain}"
    if len(local_part) == 1:
        return f"{local_part}***@{domain}"
    return f"{local_part[0]}***{local_part[-1]}@{domain}"
