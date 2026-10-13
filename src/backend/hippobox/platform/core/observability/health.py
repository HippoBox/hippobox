import asyncio
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import text

from hippobox.platform.core.cache.redis import RedisManager
from hippobox.platform.core.db.session import get_session_factory


class HealthCheckResult(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ok", "degraded"]
    checks: dict[str, str]


async def check_database() -> str:
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        return "failed"
    return "ok"


async def check_redis() -> str:
    try:
        redis = await RedisManager.get_client()
        await redis.ping()
    except Exception:
        return "failed"
    return "ok"


PROBE_TIMEOUT_SECONDS = 2.0


class DependencyCheck(BaseModel):
    status: Literal["ok", "failed", "timeout"]
    latency_ms: float


async def check_dependencies() -> dict[str, DependencyCheck]:
    async def measure(probe: Callable[[], Awaitable[str]]) -> DependencyCheck:
        started = perf_counter()
        try:
            result = await asyncio.wait_for(probe(), timeout=PROBE_TIMEOUT_SECONDS)
            status = "ok" if result == "ok" else "failed"
        except TimeoutError:
            status = "timeout"
        except Exception:
            status = "failed"
        return DependencyCheck(
            status=status, latency_ms=round((perf_counter() - started) * 1000, 1)
        )

    database, redis = await asyncio.gather(measure(check_database), measure(check_redis))
    return {"database": database, "redis": redis}


async def get_readiness() -> ReadinessResponse:
    results = await check_dependencies()
    checks = {name: result.status for name, result in results.items()}
    status = "ok" if all(result == "ok" for result in checks.values()) else "degraded"
    return ReadinessResponse(status=status, checks=checks)
