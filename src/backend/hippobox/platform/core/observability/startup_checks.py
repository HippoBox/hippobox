"""Process-local evidence from completed startup checks, never inferred health."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel


class StartupCheck(BaseModel):
    status: Literal["ok", "configured", "disabled", "unverified"]
    checked_at: datetime | None = None


STARTUP_CHECKS: dict[str, StartupCheck] = {}


def record_startup_check(name: str, status: Literal["ok", "configured", "disabled"]) -> None:
    STARTUP_CHECKS[name] = StartupCheck(status=status, checked_at=datetime.now(UTC))
