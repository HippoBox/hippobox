"""Startup-only console presentation; service checks remain owned by their callers."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from time import monotonic

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from hippobox.platform.core.config.settings import Settings
from hippobox.platform.core.observability.logging import get_logger

logger = get_logger("startup")
_CURRENT: ContextVar["StartupDisplay | None"] = ContextVar("startup_display", default=None)
_LOGO = """██████╗ ██╗  ██╗ █████╗
██╔══██╗██║  ██║██╔══██╗
██████╔╝███████║███████║
██╔══██╗╚════██║██╔══██║
██████╔╝     ██║██║  ██║
╚═════╝      ╚═╝╚═╝  ╚═╝"""


class StartupPreludeFilter(logging.Filter):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings

    def filter(self, record: logging.LogRecord) -> bool:
        if (
            self.settings.STARTUP_DISPLAY == "off"
            or record.levelno != logging.INFO
            or not isinstance(record.msg, str)
        ):
            return True
        return (record.name, record.msg) not in {
            ("uvicorn.error", "Started server process [%d]"),
            ("uvicorn.error", "Waiting for application startup."),
            ("uvicorn.error", "Application startup complete."),
            ("uvicorn.error", "Waiting for application shutdown."),
            ("uvicorn.error", "Shutting down"),
            ("uvicorn.error", "Application shutdown complete."),
            ("uvicorn.error", "Finished server process [%d]"),
            ("uvicorn.app.app.main", "App log level set to %s."),
        }


def configure_startup_console(settings: Settings) -> None:
    for name in ("uvicorn", "uvicorn.error"):
        for handler in logging.getLogger(name).handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                for existing in list(handler.filters):
                    if isinstance(existing, StartupPreludeFilter):
                        handler.removeFilter(existing)
                handler.addFilter(StartupPreludeFilter(settings))


@dataclass
class StartupRow:
    name: str
    icon: str
    stack: str
    enabled: bool
    status: str = "Pending"
    detail: str = ""
    running: bool = False


def _rows(settings: Settings) -> dict[str, StartupRow]:
    database_scheme = settings.DATABASE_URL.partition(":")[0].partition("+")[0]
    database = {"postgresql": "PostgreSQL", "postgres": "PostgreSQL", "sqlite": "SQLite"}.get(
        database_scheme, "Database"
    )
    storage = {"local": "Local", "s3": "Amazon S3", "r2": "Cloudflare R2", "supabase": "Supabase"}[
        settings.OBJECT_STORAGE_PROVIDER
    ]
    smtp = "Gmail SMTP" if settings.SMTP_HOST.lower() == "smtp.gmail.com" else "SMTP"
    stripe_mode = (
        "Live"
        if settings.STRIPE_SECRET_KEY.strip().startswith(("sk_live_", "rk_live_"))
        else "Test"
    )
    providers = (
        " · ".join(
            {"google": "Google", "github": "GitHub"}.get(provider, "Other")
            for provider in settings.oauth_provider_list
        )
        or "Not configured"
    )
    rows = {
        "storage": StartupRow("Storage", "▣", storage, True),
        "redis": StartupRow(
            "Cache", "◇", "Redis · In-memory" if settings.REDIS_IN_MEMORY else "Redis", True
        ),
        "oauth": StartupRow("OAuth", "◎", providers, settings.OAUTH_ENABLED),
        "email": StartupRow("Email", "✉", smtp, settings.EMAIL_ENABLED),
        "billing": StartupRow("Billing", "◈", f"Stripe · {stripe_mode}", settings.STRIPE_ENABLED),
        "database": StartupRow("Database", "▤", database, True),
    }
    for row in rows.values():
        if not row.enabled:
            row.status = "Not checked"
    return rows


class StartupConsoleFilter(logging.Filter):
    """Filter the console only; other handlers still receive the original LogRecord."""

    def __init__(self, handler: logging.Handler):
        super().__init__()
        self.handler = handler

    def filter(self, record: logging.LogRecord) -> bool:
        display = _CURRENT.get()
        if display is None:
            return True
        if record.name.startswith("uvicorn.app.") and record.name != logger.name:
            if record.levelno == logging.INFO:
                return False
        if record.name == logger.name and (display.live is not None or display.static_panel):
            return False
        if display.live is not None:
            # Existing StreamHandlers hold the original stderr; route through Live explicitly.
            display.console.print(Text.from_ansi(self.handler.format(record)))
            return False
        return True


class StartupDisplay:
    title = "Startup"

    def __init__(self, settings: Settings, *, console: Console | None = None):
        self.settings = settings
        self.console = console or Console(stderr=True)
        self.rows = _rows(settings)
        self.static_panel = False
        self.live: Live | None = None
        self.started_at = monotonic()
        self.outcome = "Starting services"
        self.filters: list[tuple[logging.Handler, StartupConsoleFilter]] = []

    def runtime_summary(self) -> Text:
        mode = "Production" if self.settings.APP_MODE == "production" else "Development"
        login = "Enabled" if self.settings.LOGIN_ENABLED else "Disabled · Bootstrap session"
        return Text(f"Mode: {mode}    Login: {login}", style="dim")

    def render(self) -> Panel:
        table = Table.grid(padding=(0, 2), expand=True)
        for _ in range(3 if self.title == "Shutdown" else 4):
            table.add_column()
        headers = (
            ("SERVICE", "STACK", "CLEANUP")
            if self.title == "Shutdown"
            else ("SERVICE", "STACK", "ENABLED", "CHECK")
        )
        table.add_row(*[Text(label, style="dim") for label in headers])
        table.add_row(*["" for _ in headers])
        for row in self.rows.values():
            style = (
                "red"
                if row.status == "Failed"
                else "green"
                if row.status in {"Verified", "Configured", "Ready", "Closed"}
                else "dim"
            )
            symbol = (
                "✗"
                if row.status == "Failed"
                else "✓"
                if style == "green"
                else "—"
                if row.status in {"Not checked", "Not run", "Cancelled", "Not opened"}
                else "·"
            )
            result = (
                Spinner("dots", text=row.status, style="cyan")
                if row.running
                else Text(f"{symbol} {row.status}", style=style)
            )
            if row.detail:
                result = Group(result, Text(row.detail, style="dim"))
            cells = [Text(f"{row.icon} {row.name}"), Text(row.stack)]
            if self.title != "Shutdown":
                cells.append(
                    Text("Yes" if row.enabled else "No", style=None if row.enabled else "dim")
                )
            table.add_row(*cells, result)
        footer = Text(f"{self.outcome} · {monotonic() - self.started_at:.2f}s", style="dim")
        content = [table, Text(""), footer]
        if self.title == "Startup":
            content = [self.runtime_summary(), Text(""), *content]
        return Panel(
            Group(*content),
            title=self.title,
            title_align="left",
            border_style="bright_black",
            padding=(1, 2),
            width=94,
        )

    def refresh(self) -> None:
        if self.live is not None:
            self.live.update(self.render(), refresh=True)

    def emit(self, row: StartupRow) -> None:
        logger.info(
            "%s service=%s stack=%s enabled=%s check=%s%s",
            self.title,
            row.name,
            row.stack,
            "yes" if row.enabled else "no",
            row.status,
            f" detail={row.detail}" if row.detail else "",
        )
        self.refresh()

    @contextmanager
    def activate(self) -> Iterator[None]:
        if self.settings.STARTUP_DISPLAY == "off" or not logger.isEnabledFor(logging.INFO):
            yield
            return
        interactive = (
            self.settings.STARTUP_DISPLAY == "auto"
            and self.console.is_terminal
            and not self.console.is_dumb_terminal
            and self.console.size.width >= 76
            and not self.settings.has_multiple_server_workers()
        )
        self.static_panel = (
            self.settings.STARTUP_DISPLAY == "auto"
            and not interactive
            and not self.console.is_dumb_terminal
            and self.console.size.width >= 76
            and not self.settings.has_multiple_server_workers()
        )
        self.started_at = monotonic()
        token = _CURRENT.set(self)
        try:
            for name in ("uvicorn", "uvicorn.error"):
                for handler in logging.getLogger(name).handlers:
                    if isinstance(handler, logging.StreamHandler) and not isinstance(
                        handler, logging.FileHandler
                    ):
                        console_filter = StartupConsoleFilter(handler)
                        handler.addFilter(console_filter)
                        self.filters.append((handler, console_filter))
            if interactive or self.static_panel:
                if self.title == "Startup":
                    self.console.print(Text(_LOGO, style="bold cyan"))
                    self.console.print(Text("Blueprint for Agents\n", style="dim"))
                if interactive:
                    self.live = Live(self.render(), console=self.console, refresh_per_second=8)
                    self.live.start()
                else:
                    self.console.print(Text(f"{self.outcome}…", style="dim"))
            else:
                logger.info("B4A · Blueprint for Agents · %s", self.title)
                if self.title == "Startup":
                    logger.info("%s", self.runtime_summary().plain)
            yield
        except BaseException as exc:
            for row in self.rows.values():
                if row.enabled and row.status == "Pending":
                    row.status = "Not run"
                    self.emit(row)
            self.outcome = f"{self.title} aborted ({type(exc).__name__})"
            raise
        else:
            self.outcome = (
                "Cleanup complete" if self.title == "Shutdown" else "Startup checks complete"
            )
        finally:
            self.refresh()
            try:
                if self.live is not None:
                    self.live.stop()
                elif self.static_panel:
                    self.console.print(self.render())
                logger.info("%s (%.2fs).", self.outcome, monotonic() - self.started_at)
            finally:
                self.live = None
                _CURRENT.reset(token)
                for handler, console_filter in self.filters:
                    handler.removeFilter(console_filter)
                self.filters.clear()


@contextmanager
def startup_step(name: str, *, success: str = "Verified", detail: str = "") -> Iterator[None]:
    display = _CURRENT.get()
    if display is None:
        yield
        return
    row = display.rows[name]
    if row.enabled:
        row.status = "Closing…" if display.title == "Shutdown" else "Checking…"
        row.running = True
    display.emit(row)
    try:
        yield
    except BaseException as exc:
        row.status = "Failed" if isinstance(exc, Exception) else "Cancelled"
        row.detail = type(exc).__name__  # Never render raw provider errors/credentials.
        raise
    else:
        if row.enabled:
            row.status = success
            row.detail = detail
    finally:
        row.running = False
        if row.enabled or row.status in {"Failed", "Cancelled"}:
            display.emit(row)


def startup_phase(name: str, phase: str) -> None:
    display = _CURRENT.get()
    if display is not None:
        display.rows[name].status = phase
        display.emit(display.rows[name])


class ShutdownDisplay(StartupDisplay):
    title = "Shutdown"

    def __init__(self, settings: Settings, *, redis_open: bool, console: Console | None = None):
        super().__init__(settings, console=console)
        self.rows = {
            "database": self.rows["database"],
            "redis": StartupRow(
                "Cache",
                "◇",
                "Redis · In-memory" if settings.REDIS_IN_MEMORY else "Redis",
                redis_open,
            ),
            "storage": self.rows["storage"],
        }
        if not redis_open:
            self.rows["redis"].status = "Not opened"
        self.outcome = "Closing resources"


@contextmanager
def shutdown_step(name: str) -> Iterator[None]:
    display = _CURRENT.get()
    if display is None or display.title != "Shutdown":
        yield
    else:
        with startup_step(name, success="Closed"):
            yield


def show_shutdown_farewell(settings: Settings) -> None:
    """Called only after normal lifespan exit and successful resource cleanup."""
    if settings.STARTUP_DISPLAY == "off" or not logger.isEnabledFor(logging.INFO):
        return
    console = Console(stderr=True)
    if settings.STARTUP_DISPLAY == "auto":
        console.print(Text("B4A · Bye!!", style="bold cyan"))
    else:
        logger.info("B4A · Bye!!")
