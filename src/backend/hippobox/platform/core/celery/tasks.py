"""Explicit diagnostic task; no periodic or billing work is scheduled by default."""

from hippobox.platform.core.celery.app import celery_app
from hippobox.platform.core.observability.logging import get_logger

logger = get_logger("hippobox.platform.core.celery.tasks")


@celery_app.task(name="b4fastapi.probe")
def probe() -> str:
    """Confirm broker-to-worker delivery without touching application data."""
    logger.info("Celery probe completed.")
    return "ok"
