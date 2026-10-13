"""Bounded server-side reconciliation recovers missed webhook deliveries."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select

from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.db.session import get_db
from hippobox.platform.core.observability.logging import get_logger
from hippobox.platform.models.billing import BillingCustomer
from hippobox.platform.services.billing import BillingService

logger = get_logger(__name__)


async def reconcile_subscriptions() -> None:
    if not SETTINGS.STRIPE_ENABLED:
        return
    service = BillingService()
    cutoff = datetime.now(UTC) - timedelta(minutes=5)
    async with get_db() as db:
        users = list(
            (
                await db.scalars(
                    select(BillingCustomer.user_id)
                    .where(
                        BillingCustomer.livemode == service.config().livemode,
                        BillingCustomer.stripe_customer_id.is_not(None),
                        or_(
                            BillingCustomer.subscription_synced_at.is_(None),
                            BillingCustomer.subscription_synced_at < cutoff,
                        ),
                    )
                    .order_by(
                        BillingCustomer.subscription_synced_at.asc().nulls_first(),
                        BillingCustomer.user_id,
                    )
                    .limit(50)
                )
            ).all()
        )
    for user_id in users:
        try:
            await service.sync_subscription(user_id)
        except Exception:
            logger.warning("Subscription reconciliation failed (user_id=%s).", user_id)
