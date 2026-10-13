"""Only confirmed subscription starts and applied plan changes produce mail."""

import stripe

from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.error.billing_exception import BillingErrorCode, BillingException
from hippobox.platform.models.billing import BillingCustomers
from hippobox.platform.models.inbox import INBOX
from hippobox.platform.services.billing import BillingService
from hippobox.platform.services.inbox import InboxService
from hippobox.platform.services.notifications import queue_notification


def _plan(price: str) -> str | None:
    known = BillingService._known_prices().get(price)
    if not known:
        return None
    return "Pro" if known[0].startswith("pro_") else "Plus"


def _mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def _price(obj: dict) -> str:
    items = _mapping(obj.get("items")).get("data", [])
    if not isinstance(items, list) or len(items) != 1:
        return ""
    return _mapping(_mapping(items[0]).get("price")).get("id", "")


def _invoice_price(obj: dict) -> str:
    lines = _mapping(obj.get("lines"))
    items = lines.get("data", [])
    if lines.get("has_more") or not isinstance(items, list) or len(items) != 1:
        return ""
    line = _mapping(items[0])
    return _mapping(line.get("price")).get("id", "") or _mapping(
        _mapping(line.get("pricing")).get("price_details")
    ).get("price", "")


class BillingNotificationService:
    async def receive(self, payload: bytes, signature: str) -> None:
        if not SETTINGS.STRIPE_ENABLED or not SETTINGS.STRIPE_WEBHOOK_SECRET:
            raise BillingException(BillingErrorCode.BILLING_WEBHOOK_UNAVAILABLE)
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, SETTINGS.STRIPE_WEBHOOK_SECRET
            ).to_dict()
        except (ValueError, stripe.SignatureVerificationError):
            raise BillingException(BillingErrorCode.BILLING_WEBHOOK_INVALID) from None
        if event.get("livemode") != BillingService().config().livemode:
            raise BillingException(BillingErrorCode.BILLING_WEBHOOK_INVALID)
        data = _mapping(event.get("data"))
        obj = _mapping(data.get("object"))
        customer = obj.get("customer")
        if not isinstance(customer, str):
            return
        user = await BillingCustomers.owner(customer, event["livemode"])
        if user is None:
            return
        event_type = event.get("type")
        sync_events = {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "customer.subscription.paused",
            "customer.subscription.resumed",
            "invoice.paid",
            "invoice.payment_failed",
            "invoice.payment_action_required",
            "checkout.session.completed",
            "checkout.session.async_payment_succeeded",
            "checkout.session.async_payment_failed",
            "subscription_schedule.updated",
            "subscription_schedule.released",
            "subscription_schedule.canceled",
            "subscription_schedule.completed",
            "subscription_schedule.aborted",
        }
        if event_type in sync_events:
            # Fetch current provider state under a customer lock: duplicate or older payloads
            # cannot roll the DB back to an obsolete plan. Failure returns non-2xx for redelivery.
            await BillingService().sync_subscription(user.id)
        kind, plan, key = None, None, None
        previous_key = None
        if (
            event_type == "invoice.paid"
            and obj.get("billing_reason") == "subscription_create"
            and obj.get("status") == "paid"
        ):
            sub_id = obj.get("subscription") or _mapping(
                _mapping(obj.get("parent")).get("subscription_details")
            ).get("subscription")
            if not isinstance(sub_id, str):
                return
            async with BillingService()._provider() as client:
                sub = await client.v1.subscriptions.retrieve_async(sub_id)
            if (
                sub.customer != customer
                or sub.status != "active"
                or sub.livemode != event["livemode"]
                or not _invoice_price(obj)
                or _invoice_price(obj) != _price(sub.to_dict())
            ):
                return
            plan = _plan(_price(sub.to_dict()))
            kind, key = "subscription_started", f"subscription-started:{sub_id}"
        elif (
            event_type == "customer.subscription.updated"
            and isinstance(obj.get("id"), str)
            and isinstance(event.get("id"), str)
        ):
            previous = _mapping(data.get("previous_attributes"))
            old_price, new_price = _price(previous), _price(obj)
            if (
                not old_price
                or not new_price
                or old_price == new_price
                or obj.get("status") != "active"
                or obj.get("pending_update")
            ):
                return
            async with BillingService()._provider() as client:
                sub = await client.v1.subscriptions.retrieve_async(obj["id"])
            if (
                sub.customer != customer
                or sub.status != "active"
                or sub.livemode != event["livemode"]
                or _price(sub.to_dict()) != new_price
                or getattr(sub, "pending_update", None)
            ):
                return  # A delayed/out-of-order event must not describe an obsolete plan.
            plan = _plan(new_price)
            kind, key = (
                "plan_changed",
                f"plan-changed:{obj['id']}:{event['id']}",
            )
            if isinstance(event.get("created"), int):
                previous_key = (
                    f"plan-changed:{obj['id']}:{event['created']}:{old_price}:{new_price}"
                )
        elif (
            event_type == "customer.subscription.deleted"
            and _mapping(obj.get("cancellation_details")).get("reason") == "cancellation_requested"
        ):
            if not isinstance(obj.get("id"), str) or obj.get("status") != "canceled":
                return
            async with BillingService()._provider() as client:
                if await BillingService()._subscriptions(client, customer):
                    return  # A newer subscription must not be reported as Free.
            kind, plan, key = "plan_changed", "Free", f"subscription-ended:{obj['id']}"
        if kind is None or plan is None:
            return
        created = await INBOX.deliver(
            key=key,
            user_id=user.id,
            kind=kind,
            title="Subscription started" if kind == "subscription_started" else "Plan changed",
            body=plan,
            action_path="/settings?section=billing",
        )
        if created:
            await InboxService().changed(user.id)
        if not SETTINGS.EMAIL_ENABLED:
            return
        # Provider customer locales survive invoice metadata differences and delayed events.
        async with BillingService()._provider() as client:
            recipient = await client.v1.customers.retrieve_async(customer)
        if recipient.id != customer or recipient.livemode != event["livemode"]:
            raise BillingException(BillingErrorCode.BILLING_WEBHOOK_INVALID)
        locales = getattr(recipient, "preferred_locales", []) or []
        language = next(
            (
                locale.split("-")[0].lower()
                for locale in locales
                if isinstance(locale, str) and locale.split("-")[0].lower() in ("ko", "en")
            ),
            "en",
        )
        await queue_notification(
            key,
            kind,
            previous_key=previous_key,
            email=user.email,
            name=user.name,
            plan=plan,
            language=language,
        )
