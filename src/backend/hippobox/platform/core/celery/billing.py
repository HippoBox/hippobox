"""Refresh stale DB subscription snapshots without browser polling."""

import asyncio

from hippobox.platform.core.celery.app import celery_app
from hippobox.platform.core.db.session import dispose_db


@celery_app.task(name="b4fastapi.billing.reconcile")
def reconcile_billing() -> None:
    from hippobox.platform.services.billing_reconciliation import reconcile_subscriptions

    async def run():
        try:
            await reconcile_subscriptions()
        finally:
            await dispose_db()

    asyncio.run(run())
