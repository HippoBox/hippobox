"""Outbox drain task; Beat recovers broker outages and expired worker leases."""

import asyncio

from hippobox.platform.core.celery.app import celery_app
from hippobox.platform.core.db.session import dispose_db


@celery_app.task(name="b4fastapi.notifications.drain")
def drain_notifications() -> None:
    from hippobox.platform.services.notifications import deliver_notifications

    async def run():
        try:
            await deliver_notifications()
        finally:
            await dispose_db()

    asyncio.run(run())
