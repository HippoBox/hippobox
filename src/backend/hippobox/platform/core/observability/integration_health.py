"""Bounded, per-process single-flight provider checks requested by administrators."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from time import monotonic
from typing import Literal

from pydantic import BaseModel

CACHE_SECONDS = 60.0
RESPONSE_TIMEOUT_SECONDS = 5.0


class IntegrationCheck(BaseModel):
    status: Literal["ok", "failed", "timeout", "disabled"]
    latency_ms: float | None = None
    checked_at: datetime


class IntegrationHealth:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, IntegrationCheck]] = {}
        self._pending: dict[str, asyncio.Task[IntegrationCheck]] = {}

    async def check(
        self, name: str, enabled: bool, probe: Callable[[], Awaitable[None]]
    ) -> IntegrationCheck:
        if not enabled:
            return IntegrationCheck(status="disabled", checked_at=datetime.now(UTC))
        cached = self._cache.get(name)
        if cached and monotonic() - cached[0] < CACHE_SECONDS:
            return cached[1].model_copy()
        task = self._pending.get(name)
        if task is None or task.done():
            task = asyncio.create_task(self._run(name, probe))
            self._pending[name] = task
        try:
            # A canceled browser request must not start duplicate SMTP/Stripe probes.
            return await asyncio.wait_for(asyncio.shield(task), RESPONSE_TIMEOUT_SECONDS)
        except TimeoutError:
            return IntegrationCheck(status="timeout", checked_at=datetime.now(UTC))

    async def _run(self, name: str, probe: Callable[[], Awaitable[None]]) -> IntegrationCheck:
        started = monotonic()
        try:
            await probe()
            status = "ok"
        except TimeoutError:
            status = "timeout"
        except Exception:
            status = "failed"
        result = IntegrationCheck(
            status=status,
            checked_at=datetime.now(UTC),
            latency_ms=round((monotonic() - started) * 1000, 1),
        )
        self._cache[name] = (monotonic(), result)
        return result

    async def reset(self) -> None:
        tasks = list(self._pending.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._pending.clear()
        self._cache.clear()


INTEGRATION_HEALTH = IntegrationHealth()
