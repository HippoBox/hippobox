"""Hosted registration and subscriptions; Stripe remains the billing source of truth."""

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import stripe

from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.error.billing_exception import BillingErrorCode, BillingException
from hippobox.platform.core.observability.logging import get_logger
from hippobox.platform.core.observability.service import observe_service
from hippobox.platform.models.billing import (
    BillingAddress,
    BillingCardSetupResponse,
    BillingCardSetupStatus,
    BillingChangeForm,
    BillingCheckoutForm,
    BillingCheckouts,
    BillingCheckoutStatusResponse,
    BillingConfigResponse,
    BillingCustomers,
    BillingInvoiceDetail,
    BillingInvoiceLine,
    BillingInvoiceResponse,
    BillingInvoicesResponse,
    BillingMethodForm,
    BillingPaymentMethodResponse,
    BillingPaymentMethodsResponse,
    BillingPlansResponse,
    BillingPortalForm,
    BillingPriceResponse,
    BillingProfileForm,
    BillingProfileResponse,
    BillingSetupForm,
    BillingSetupResponse,
    BillingSetupStatusResponse,
    BillingSubscriptionResponse,
)

logger = get_logger("hippobox.platform.service.billing")


class BillingService:
    def _configuration_errors(self) -> list[str]:
        key = SETTINGS.STRIPE_SECRET_KEY.strip()
        prefixes = ("sk_test_", "rk_test_", "sk_live_", "rk_live_")
        livemode = key.startswith(("sk_live_", "rk_live_"))
        errors = []
        if not any(key.startswith(prefix) and len(key) > len(prefix) for prefix in prefixes):
            errors.append("STRIPE_SECRET_KEY must be a Stripe secret or restricted API key.")
        for name, url in (
            ("STRIPE_SETUP_SUCCESS_URL", SETTINGS.STRIPE_SETUP_SUCCESS_URL),
            ("STRIPE_SETUP_CANCEL_URL", SETTINGS.STRIPE_SETUP_CANCEL_URL),
        ):
            if not self._valid_url(url, livemode):
                errors.append(
                    f"{name} must be an absolute HTTP(S) URL without credentials or a fragment; "
                    "live mode requires HTTPS."
                )
        if SETTINGS.STRIPE_ENABLED:
            for name in ("STRIPE_CHECKOUT_SUCCESS_URL", "STRIPE_CHECKOUT_CANCEL_URL"):
                if not self._valid_url(getattr(SETTINGS, name), livemode):
                    errors.append(f"{name} must be a valid absolute return URL.")
            if "{CHECKOUT_SESSION_ID}" not in SETTINGS.STRIPE_CHECKOUT_SUCCESS_URL:
                errors.append("STRIPE_CHECKOUT_SUCCESS_URL must contain {CHECKOUT_SESSION_ID}.")
            for price in self._price_ids().values():
                if not price.startswith("price_"):
                    errors.append("All subscription Price IDs must be configured.")
        if "{CHECKOUT_SESSION_ID}" not in SETTINGS.STRIPE_SETUP_SUCCESS_URL:
            errors.append("STRIPE_SETUP_SUCCESS_URL must contain {CHECKOUT_SESSION_ID}.")
        public_key = SETTINGS.STRIPE_PUBLISHABLE_KEY.strip()
        if public_key and not public_key.startswith("pk_live_" if livemode else "pk_test_"):
            errors.append(
                "STRIPE_PUBLISHABLE_KEY must be a public key matching the secret key mode."
            )
        return errors

    def config(self) -> BillingConfigResponse:
        return BillingConfigResponse(
            enabled=SETTINGS.STRIPE_ENABLED and not self._configuration_errors(),
            livemode=SETTINGS.STRIPE_SECRET_KEY.strip().startswith(("sk_live_", "rk_live_")),
            publishable_key=SETTINGS.STRIPE_PUBLISHABLE_KEY.strip() or None,
        )

    async def check_connection(self) -> None:
        """Check API authentication without creating a billing resource."""
        async with self._provider() as client:
            await client.v1.checkout.sessions.list_async(params={"limit": 1})

    async def initialize(self) -> None:
        if not SETTINGS.STRIPE_ENABLED:
            logger.info("Stripe integration is disabled.")
            return
        errors = self._configuration_errors()
        if errors:
            raise RuntimeError("Invalid Stripe configuration: " + " ".join(errors))
        mode = "live" if self.config().livemode else "test"
        logger.info("Stripe startup verification started (mode=%s).", mode)
        try:
            async with self._provider() as client:
                try:
                    # Authenticate against the API this integration actually uses.
                    # Read at most one entry; never create resources or log its contents.
                    await client.v1.checkout.sessions.list_async(params={"limit": 1})
                    if SETTINGS.STRIPE_PORTAL_CONFIGURATION_ID:
                        await self._portal_configuration(client)
                    if SETTINGS.STRIPE_ENABLED:
                        for (plan, currency), price_id in self._price_ids().items():
                            await self._price(client, plan, currency, price_id)
                except stripe.AuthenticationError:
                    raise RuntimeError(
                        "Stripe startup verification failed: authentication rejected. "
                        "Check STRIPE_SECRET_KEY."
                    ) from None
                except stripe.PermissionError:
                    raise RuntimeError(
                        "Stripe startup verification failed: Billing read permission denied. "
                        "Check the Stripe API key permissions."
                    ) from None
        except BillingException as error:
            if error.code.error == "BILLING_PLAN_UNAVAILABLE":
                raise RuntimeError(
                    "Stripe startup verification failed: configured billing resources do not match the required plan, currency, portal policy or mode."
                ) from None
            raise RuntimeError(
                "Stripe startup verification failed: Billing API request failed or timed out. "
                "Check network connectivity, Stripe availability and API key permissions."
            ) from None
        logger.info("Stripe startup verification succeeded (mode=%s).", mode)

    @staticmethod
    def _valid_url(url: str, livemode: bool) -> bool:
        try:
            parsed = urlsplit(url)
            _ = parsed.port  # Reject malformed/out-of-range ports during configuration validation.
            return bool(
                parsed.scheme in ("http", "https")
                and parsed.hostname
                and not parsed.username
                and not parsed.password
                and not parsed.fragment
                and (not livemode or parsed.scheme == "https")
            )
        except ValueError:
            return False

    @asynccontextmanager
    async def _provider(self) -> AsyncIterator[stripe.StripeClient]:
        if not self.config().enabled:
            raise BillingException(BillingErrorCode.BILLING_DISABLED)
        http = stripe.HTTPXClient(timeout=5)
        client = stripe.StripeClient(
            SETTINGS.STRIPE_SECRET_KEY.strip(), http_client=http, max_network_retries=1
        )
        try:
            async with asyncio.timeout(20):
                yield client
        except (stripe.StripeError, TimeoutError):
            # Never expose provider exception text, keys, URLs or payment payloads.
            raise BillingException(BillingErrorCode.BILLING_UNAVAILABLE) from None
        finally:
            await http.close_async()
            http.close()

    async def _customer(self, client: stripe.StripeClient, user_id: int) -> str:
        livemode = self.config().livemode
        row = await BillingCustomers.reserve(user_id, livemode)
        if row.stripe_customer_id:
            return row.stripe_customer_id
        created = row.created_at.replace(tzinfo=UTC)
        # Stripe may prune idempotency keys after 24h. Do not create a duplicate
        # after an ambiguous remote success/local commit failure outside that window.
        if datetime.now(UTC) - created >= timedelta(hours=23):
            raise BillingException(BillingErrorCode.BILLING_RECONCILIATION_REQUIRED)
        customer = await client.v1.customers.create_async(
            params={"metadata": {"billing_identity": row.creation_key, "user_id": str(user_id)}},
            options={"idempotency_key": f"billing-customer:{row.creation_key}"},
        )
        return await BillingCustomers.bind(user_id, livemode, customer.id)

    @observe_service("billing.create_setup")
    async def create_setup(self, user_id: int, form: BillingSetupForm) -> BillingSetupResponse:
        async with self._provider() as client:
            customer_id = await self._customer(client, user_id)
            session = await client.v1.checkout.sessions.create_async(
                params={
                    "mode": "setup",
                    "customer": customer_id,
                    "client_reference_id": str(user_id),
                    "payment_method_types": ["card", "link"],
                    "success_url": SETTINGS.STRIPE_SETUP_SUCCESS_URL,
                    "cancel_url": SETTINGS.STRIPE_SETUP_CANCEL_URL,
                    "setup_intent_data": {"metadata": {"user_id": str(user_id)}},
                },
                options={"idempotency_key": f"billing-setup:{customer_id}:{form.request_id}"},
            )
            if not session.url:
                raise BillingException(BillingErrorCode.BILLING_UNAVAILABLE)
            return BillingSetupResponse(id=session.id, url=session.url)

    @observe_service("billing.setup_status")
    async def setup_status(self, user_id: int, session_id: str) -> BillingSetupStatusResponse:
        async with self._provider() as client:
            row = await BillingCustomers.get(user_id, self.config().livemode)
            if row is None or row.stripe_customer_id is None:
                raise BillingException(BillingErrorCode.BILLING_NOT_FOUND)
            try:
                session = await client.v1.checkout.sessions.retrieve_async(
                    session_id, params={"expand": ["setup_intent"]}
                )
            except stripe.InvalidRequestError as exc:
                if exc.code == "resource_missing":
                    raise BillingException(BillingErrorCode.BILLING_NOT_FOUND) from None
                raise
            if (
                session.mode != "setup"
                or session.customer != row.stripe_customer_id
                or session.client_reference_id != str(user_id)
                or session.livemode != row.livemode
            ):
                raise BillingException(BillingErrorCode.BILLING_NOT_FOUND)
            intent = session.setup_intent
            registered = bool(
                session.status == "complete"
                and intent
                and not isinstance(intent, str)
                and intent.status == "succeeded"
                and intent.customer == row.stripe_customer_id
                and getattr(intent, "livemode", None) == row.livemode
                and intent.payment_method
            )
            return BillingSetupStatusResponse(
                id=session.id, status=session.status, registered=registered
            )

    @observe_service("billing.list_payment_methods")
    async def list_payment_methods(
        self,
        user_id: int,
        method_type: Literal["card", "link"],
        limit: int,
        starting_after: str | None,
    ) -> BillingPaymentMethodsResponse:
        async with self._provider() as client:
            row = await BillingCustomers.get(user_id, self.config().livemode)
            if row is None or row.stripe_customer_id is None:
                return BillingPaymentMethodsResponse(items=[], has_more=False)
            params = {"type": method_type, "limit": limit}
            if starting_after:
                params["starting_after"] = starting_after
            methods = await client.v1.customers.payment_methods.list_async(
                row.stripe_customer_id, params=params
            )
            items = []
            for method in methods.data:
                card = method.card if method.type == "card" else None
                items.append(
                    BillingPaymentMethodResponse(
                        id=method.id,
                        type=method.type,
                        brand=card.brand if card else None,
                        last4=card.last4 if card else None,
                        exp_month=card.exp_month if card else None,
                        exp_year=card.exp_year if card else None,
                    )
                )
            return BillingPaymentMethodsResponse(
                items=items,
                has_more=methods.has_more,
                next_cursor=items[-1].id if methods.has_more and items else None,
            )

    @staticmethod
    def _price_ids() -> dict[tuple[str, str], str]:
        prices = {}
        for tier in ("plus", "pro"):
            for interval in ("monthly", "annual"):
                plan = interval if tier == "plus" else f"pro_{interval}"
                for currency in ("krw", "usd"):
                    price = getattr(
                        SETTINGS,
                        f"STRIPE_{tier.upper()}_{interval.upper()}_{currency.upper()}_PRICE_ID",
                    ).strip()
                    if tier == "plus" and not price:
                        price = getattr(
                            SETTINGS, f"STRIPE_{interval.upper()}_{currency.upper()}_PRICE_ID"
                        ).strip()
                    if price or tier == "plus":
                        prices[(plan, currency)] = price
        return prices

    @classmethod
    def _known_prices(cls) -> dict[str, tuple[str, str]]:
        # Preserve existing subscriptions when new purchase prices change.
        legacy = {
            getattr(SETTINGS, f"STRIPE_{interval.upper()}_{currency.upper()}_PRICE_ID").strip(): (
                interval,
                currency,
            )
            for interval in ("monthly", "annual")
            for currency in ("krw", "usd")
        }
        legacy.update({value: key for key, value in cls._price_ids().items() if value})
        legacy.pop("", None)
        return legacy

    async def _price(
        self, client: stripe.StripeClient, plan: str, currency: str, price_id: str
    ) -> BillingPriceResponse:
        price = await client.v1.prices.retrieve_async(price_id)
        recurring = price.recurring
        if (
            not price.active
            or price.livemode != self.config().livemode
            or price.currency != currency
            or price.unit_amount is None
            or price.unit_amount <= 0
            or price.billing_scheme != "per_unit"
            or not recurring
            or recurring.interval != ("month" if plan.endswith("monthly") else "year")
            or recurring.interval_count != 1
            or recurring.usage_type != "licensed"
        ):
            raise BillingException(BillingErrorCode.BILLING_PLAN_UNAVAILABLE)
        return BillingPriceResponse(plan=plan, currency=currency, amount=price.unit_amount)

    @observe_service("billing.plans")
    async def plans(self) -> BillingPlansResponse:
        config = self.config()
        if not config.enabled:
            return BillingPlansResponse(enabled=False, livemode=config.livemode, prices=[])
        async with self._provider() as client:
            prices = [
                await self._price(client, plan, currency, price_id)
                for (plan, currency), price_id in self._price_ids().items()
            ]
        return BillingPlansResponse(enabled=True, livemode=config.livemode, prices=prices)

    async def _subscriptions(
        self, client: stripe.StripeClient, customer_id: str
    ) -> list[stripe.Subscription]:
        subscriptions = await client.v1.subscriptions.list_async(
            params={
                "customer": customer_id,
                "status": "all",
                "limit": 100,
            }
        )
        # Never silently treat an incomplete page as Free or permit another purchase.
        if subscriptions.has_more:
            raise BillingException(BillingErrorCode.BILLING_RECONCILIATION_REQUIRED)
        return [
            item
            for item in subscriptions.data
            if item.status not in ("canceled", "incomplete_expired")
        ]

    def _subscription_response(
        self, subscription: stripe.Subscription
    ) -> BillingSubscriptionResponse:
        items = subscription["items"].data
        mapped = self._known_prices()
        match = mapped.get(items[0].price.id) if len(items) == 1 else None
        return BillingSubscriptionResponse(
            plan=match[0] if match else "unknown",
            status=subscription.status,
            currency=subscription.currency,
            current_period_end=getattr(items[0], "current_period_end", None)
            if len(items) == 1
            else None,
            cancel_at_period_end=subscription.cancel_at_period_end,
            has_subscription=True,
        )

    @staticmethod
    def _save_subscription(
        row, snapshot: BillingSubscriptionResponse, subscription_id: str | None = None
    ) -> BillingSubscriptionResponse:
        row.stripe_subscription_id = subscription_id
        row.subscription_snapshot = snapshot.model_dump(mode="json")
        row.subscription_synced_at = datetime.now(UTC)
        return snapshot

    async def sync_subscription(
        self, user_id: int, *, only_missing: bool = False
    ) -> BillingSubscriptionResponse:
        if not SETTINGS.STRIPE_ENABLED:
            raise BillingException(BillingErrorCode.BILLING_DISABLED)
        async with BillingCustomers.locked(user_id, self.config().livemode) as row:
            if row is None or row.stripe_customer_id is None:
                return BillingSubscriptionResponse(plan="free", status="none")
            if only_missing and row.subscription_snapshot is not None:
                return BillingSubscriptionResponse.model_validate(row.subscription_snapshot)
            async with self._provider() as client:
                subscriptions = await self._subscriptions(client, row.stripe_customer_id)
                if len(subscriptions) > 1:
                    # Persist uncertainty rather than continuing to advertise an old tier.
                    snapshot = BillingSubscriptionResponse(
                        plan="unknown", status="reconciliation_required", has_subscription=True
                    )
                else:
                    snapshot = (
                        await self._managed_response(client, subscriptions[0])
                        if subscriptions
                        else BillingSubscriptionResponse(plan="free", status="none")
                    )
                return self._save_subscription(
                    row, snapshot, subscriptions[0].id if len(subscriptions) == 1 else None
                )

    @observe_service("billing.subscription")
    async def subscription(self, user_id: int) -> BillingSubscriptionResponse:
        if not SETTINGS.STRIPE_ENABLED:
            raise BillingException(BillingErrorCode.BILLING_DISABLED)
        row = await BillingCustomers.get(user_id, self.config().livemode)
        if row is None or row.stripe_customer_id is None:
            return BillingSubscriptionResponse(plan="free", status="none")
        if row.subscription_snapshot is not None:
            return BillingSubscriptionResponse.model_validate(row.subscription_snapshot)
        # Existing installations backfill a customer's snapshot once, under a DB lock.
        return await self.sync_subscription(user_id, only_missing=True)

    @observe_service("billing.create_checkout")
    async def create_checkout(
        self, user_id: int, form: BillingCheckoutForm
    ) -> BillingSetupResponse:
        if not SETTINGS.STRIPE_ENABLED:
            raise BillingException(BillingErrorCode.BILLING_DISABLED)
        async with self._provider() as client:
            price_id = self._price_ids().get((form.plan, form.currency))
            if not price_id:
                raise BillingException(BillingErrorCode.BILLING_PLAN_UNAVAILABLE)
            await self._price(client, form.plan, form.currency, price_id)
            customer_id = await self._customer(client, user_id)
            reservation = await BillingCheckouts.reserve(user_id, self.config().livemode, price_id)
            # This read follows reservation so a just-completed expired attempt is observed.
            if await self._subscriptions(client, customer_id):
                raise BillingException(BillingErrorCode.BILLING_CHECKOUT_CONFLICT)
            expires_at = int(reservation.expires_at.replace(tzinfo=UTC).timestamp())
            if (
                reservation.price_id != price_id
                or expires_at - int(datetime.now(UTC).timestamp()) < 31 * 60
            ):
                # Never change the parameters of an ambiguous reserved attempt or extend it.
                raise BillingException(BillingErrorCode.BILLING_CHECKOUT_CONFLICT)
            session = await client.v1.checkout.sessions.create_async(
                params={
                    "mode": "subscription",
                    "customer": customer_id,
                    "client_reference_id": str(user_id),
                    "line_items": [{"price": price_id, "quantity": 1}],
                    "payment_method_types": ["card", "link"],
                    "success_url": SETTINGS.STRIPE_CHECKOUT_SUCCESS_URL,
                    "cancel_url": SETTINGS.STRIPE_CHECKOUT_CANCEL_URL,
                    "expires_at": expires_at,
                    "subscription_data": {"metadata": {"user_id": str(user_id)}},
                },
                options={
                    "idempotency_key": f"billing-checkout:{customer_id}:{reservation.creation_key}"
                },
            )
            if session.status != "open" or not session.url:
                raise BillingException(BillingErrorCode.BILLING_CHECKOUT_CONFLICT)
            return BillingSetupResponse(id=session.id, url=session.url)

    @observe_service("billing.checkout_status")
    async def checkout_status(self, user_id: int, session_id: str) -> BillingCheckoutStatusResponse:
        if not SETTINGS.STRIPE_ENABLED:
            raise BillingException(BillingErrorCode.BILLING_DISABLED)
        async with self._provider() as client:
            row = await BillingCustomers.get(user_id, self.config().livemode)
            if row is None or row.stripe_customer_id is None:
                raise BillingException(BillingErrorCode.BILLING_NOT_FOUND)
            try:
                session = await client.v1.checkout.sessions.retrieve_async(
                    session_id, params={"expand": ["subscription"]}
                )
            except stripe.InvalidRequestError as exc:
                if exc.code == "resource_missing":
                    raise BillingException(BillingErrorCode.BILLING_NOT_FOUND) from None
                raise
            if (
                session.mode != "subscription"
                or session.customer != row.stripe_customer_id
                or session.client_reference_id != str(user_id)
                or session.livemode != row.livemode
            ):
                raise BillingException(BillingErrorCode.BILLING_NOT_FOUND)
            subscription = session.subscription
            paid = bool(
                session.status == "complete"
                and session.payment_status == "paid"
                and subscription
                and not isinstance(subscription, str)
                and subscription.customer == row.stripe_customer_id
                and getattr(subscription, "livemode", None) == row.livemode
                and subscription.status == "active"
            )
            if session.status == "complete":
                await self.sync_subscription(user_id)
            return BillingCheckoutStatusResponse(id=session.id, status=session.status, paid=paid)

    async def _managed_response(
        self, client: stripe.StripeClient, subscription: stripe.Subscription
    ) -> BillingSubscriptionResponse:
        result = self._subscription_response(subscription)
        pending_update = getattr(subscription, "pending_update", None)
        result.payment_required = bool(pending_update)
        if pending_update:
            invoice_id = getattr(subscription, "latest_invoice", None)
            if invoice_id:
                invoice = await client.v1.invoices.retrieve_async(invoice_id)
                if (
                    invoice.customer != subscription.customer
                    or invoice.livemode != self.config().livemode
                ):
                    raise BillingException(BillingErrorCode.BILLING_NOT_FOUND)
                url = getattr(invoice, "hosted_invoice_url", None)
                parsed = urlsplit(url) if url else None
                if (
                    parsed
                    and parsed.scheme == "https"
                    and parsed.hostname in ("invoice.stripe.com", "pay.stripe.com")
                    and not parsed.username
                    and not parsed.password
                    and not parsed.port
                ):
                    result.payment_url = url
        item = subscription["items"].data[0] if len(subscription["items"].data) == 1 else None
        schedule_id = getattr(subscription, "schedule", None)
        schedule = (
            await client.v1.subscription_schedules.retrieve_async(schedule_id)
            if schedule_id
            else None
        )
        owned = not schedule or (
            getattr(schedule.metadata, "b4a_managed", None) == "period_end_v1"
            and schedule.customer == subscription.customer
        )
        result.can_manage = bool(
            SETTINGS.STRIPE_ENABLED
            and subscription.status == "active"
            and not pending_update
            and result.plan in ("monthly", "annual", "pro_monthly", "pro_annual")
            and result.current_period_end
            and item
            and getattr(item, "quantity", 1) == 1
            and getattr(subscription, "collection_method", "charge_automatically")
            == "charge_automatically"
            and not getattr(subscription, "discounts", [])
            and not getattr(subscription, "default_tax_rates", [])
            and not getattr(item, "discounts", [])
            and not getattr(item, "tax_rates", [])
            and not getattr(subscription, "trial_end", None)
            and not getattr(subscription, "pause_collection", None)
            and not getattr(subscription, "transfer_data", None)
            and owned
        )
        if subscription.cancel_at_period_end:
            result.pending_plan = "free"
            result.pending_effective_at = result.current_period_end
        future = []
        if schedule:
            future = (
                [
                    phase
                    for phase in schedule.phases
                    if phase.start_date >= result.current_period_end
                ]
                if result.current_period_end
                else []
            )
            if owned and future:
                phase = future[0]
                price = phase["items"][0].price if len(phase["items"]) == 1 else None
                mapped = self._known_prices()
                match = mapped.get(price if isinstance(price, str) else getattr(price, "id", None))
                if match:
                    result.pending_plan = match[0]
                    result.pending_effective_at = phase.start_date
                else:
                    result.can_manage = False
        result.change_version = hashlib.sha256(
            json.dumps(
                {
                    "id": subscription.id,
                    "plan": result.plan,
                    "currency": result.currency,
                    "status": result.status,
                    "end": result.current_period_end,
                    "cancel": subscription.cancel_at_period_end,
                    "schedule": schedule_id,
                    "future": [phase.to_dict() for phase in future],
                    "pending_update_expires_at": getattr(pending_update, "expires_at", None),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        return result

    @observe_service("billing.change_subscription")
    async def change_subscription(
        self, user_id: int, form: BillingChangeForm
    ) -> BillingSubscriptionResponse:
        try:
            return await self._change_subscription(user_id, form)
        except BillingException as exc:
            if exc.code.error == "BILLING_CHANGE_CONFLICT":
                # Refresh after the failed mutation releases its customer lock.
                # The user can then explicitly reload the current version and retry.
                await self.sync_subscription(user_id)
            raise

    async def _change_subscription(
        self, user_id: int, form: BillingChangeForm
    ) -> BillingSubscriptionResponse:
        if not SETTINGS.STRIPE_ENABLED:
            raise BillingException(BillingErrorCode.BILLING_DISABLED)
        async with (
            self._provider() as client,
            BillingCustomers.locked(user_id, self.config().livemode) as row,
        ):
            if row is None or not row.stripe_customer_id:
                raise BillingException(BillingErrorCode.BILLING_NOT_FOUND)
            subscriptions = await self._subscriptions(client, row.stripe_customer_id)
            if len(subscriptions) != 1:
                raise BillingException(BillingErrorCode.BILLING_CHANGE_CONFLICT)
            subscription = subscriptions[0]
            current = await self._managed_response(client, subscription)
            prefix = f"billing-change:{subscription.id}:{form.request_id}"
            schedule_id = getattr(subscription, "schedule", None)
            if (
                schedule_id
                and not current.can_manage
                and form.plan in ("monthly", "annual", "pro_monthly", "pro_annual")
            ):
                schedule = await client.v1.subscription_schedules.retrieve_async(schedule_id)
                # Recover only the exact creation request Stripe has already accepted.
                # An unrelated request key cannot create a second schedule on this subscription.
                snapshot = subscription.to_dict()
                snapshot["schedule"] = None
                original = stripe.Subscription.construct_from(snapshot, SETTINGS.STRIPE_SECRET_KEY)
                original_state = await self._managed_response(client, original)
                phases = list(schedule.phases)
                unchanged = len(phases) <= 1 and not schedule.to_dict().get("metadata", {})
                if phases:
                    phase_items = phases[0]["items"]
                    unchanged = (
                        unchanged
                        and len(phase_items) == 1
                        and phase_items[0].price == subscription["items"].data[0].price.id
                        and getattr(phase_items[0], "quantity", 1) == 1
                    )
                if (
                    unchanged
                    and original_state.can_manage
                    and original_state.change_version == form.expected_version
                ):
                    created = await client.v1.subscription_schedules.create_async(
                        params={"from_subscription": subscription.id},
                        options={"idempotency_key": prefix + ":create"},
                    )
                    if created.id == schedule_id and created.customer == subscription.customer:
                        current = original_state
            if (
                not current.can_manage
                or current.change_version != form.expected_version
                or (
                    form.plan in ("monthly", "annual", "pro_monthly", "pro_annual")
                    and current.current_period_end <= int(datetime.now(UTC).timestamp()) + 60
                )
            ):
                raise BillingException(BillingErrorCode.BILLING_CHANGE_CONFLICT)
            if subscription.customer != row.stripe_customer_id:
                raise BillingException(BillingErrorCode.BILLING_NOT_FOUND)
            target = form.plan
            if target == current.plan:
                target = "keep"
            prefix = f"billing-change:{subscription.id}:{form.request_id}"
            schedule_id = getattr(subscription, "schedule", None)
            if target in ("free", "keep"):
                if schedule_id:
                    await client.v1.subscription_schedules.release_async(
                        schedule_id,
                        params={"preserve_cancel_date": False},
                        options={"idempotency_key": prefix + ":release"},
                    )
                await client.v1.subscriptions.update_async(
                    subscription.id,
                    params={"cancel_at_period_end": target == "free", "proration_behavior": "none"},
                    options={"idempotency_key": prefix + ":cancel"},
                )
            else:
                price_id = self._price_ids().get((target, current.currency))
                if not price_id:
                    raise BillingException(BillingErrorCode.BILLING_PLAN_UNAVAILABLE)
                await self._price(client, target, current.currency, price_id)
                # A higher tier is available only after Stripe collects the prorated charge.
                upgrading = target.startswith("pro_") and current.plan in ("monthly", "annual")
                if upgrading:
                    if schedule_id:
                        await client.v1.subscription_schedules.release_async(
                            schedule_id,
                            params={"preserve_cancel_date": True},
                            options={"idempotency_key": prefix + ":release-upgrade"},
                        )
                    item = subscription["items"].data[0]
                    updated = await client.v1.subscriptions.update_async(
                        subscription.id,
                        params={
                            "items": [{"id": item.id, "price": price_id, "quantity": 1}],
                            "payment_behavior": "pending_if_incomplete",
                            "proration_behavior": "always_invoice",
                            "cancel_at_period_end": False,
                        },
                        options={"idempotency_key": prefix + ":upgrade"},
                    )
                    return self._save_subscription(
                        row, await self._managed_response(client, updated), updated.id
                    )
                if subscription.cancel_at_period_end:
                    await client.v1.subscriptions.update_async(
                        subscription.id,
                        params={"cancel_at_period_end": False, "proration_behavior": "none"},
                        options={"idempotency_key": prefix + ":resume"},
                    )
                if not schedule_id:
                    schedule = await client.v1.subscription_schedules.create_async(
                        params={"from_subscription": subscription.id},
                        options={"idempotency_key": prefix + ":create"},
                    )
                    schedule_id = schedule.id
                else:
                    schedule = await client.v1.subscription_schedules.retrieve_async(schedule_id)
                item = subscription["items"].data[0]
                await client.v1.subscription_schedules.update_async(
                    schedule_id,
                    params={
                        "end_behavior": "release",
                        "proration_behavior": "none",
                        "metadata": {"b4a_managed": "period_end_v1"},
                        "phases": [
                            {
                                "start_date": schedule.current_phase.start_date,
                                "end_date": current.current_period_end,
                                "items": [{"price": item.price.id, "quantity": 1}],
                                "proration_behavior": "none",
                            },
                            {
                                "start_date": current.current_period_end,
                                "duration": {
                                    "interval": "month" if target.endswith("monthly") else "year",
                                    "interval_count": 1,
                                },
                                "items": [{"price": price_id, "quantity": 1}],
                                "proration_behavior": "none",
                                "billing_cycle_anchor": "phase_start",
                            },
                        ],
                    },
                    options={"idempotency_key": prefix + ":update"},
                )
            updated = await client.v1.subscriptions.retrieve_async(subscription.id)
            return self._save_subscription(
                row, await self._managed_response(client, updated), updated.id
            )

    @observe_service("billing.profile")
    async def profile(self, user_id: int) -> BillingProfileResponse:
        async with self._provider() as client:
            row = await BillingCustomers.get(user_id, self.config().livemode)
            if not row or not row.stripe_customer_id:
                return BillingProfileResponse(
                    portal_enabled=bool(SETTINGS.STRIPE_PORTAL_CONFIGURATION_ID)
                )
            customer = await client.v1.customers.retrieve_async(row.stripe_customer_id)
            if getattr(customer, "deleted", False):
                raise BillingException(BillingErrorCode.BILLING_RECONCILIATION_REQUIRED)
            address = getattr(customer, "address", None)
            default = getattr(customer.invoice_settings, "default_payment_method", None)
            subscriptions = await self._subscriptions(client, row.stripe_customer_id)
            if len(subscriptions) == 1:
                default = getattr(subscriptions[0], "default_payment_method", None) or default
            return BillingProfileResponse(
                email=getattr(customer, "email", None),
                name=getattr(customer, "name", None),
                address=[
                    str(getattr(address, key))
                    for key in ("line1", "line2", "city", "state", "postal_code", "country")
                    if address and getattr(address, key, None)
                ],
                address_fields=BillingAddress(
                    **{
                        key: getattr(address, key, None) or ""
                        for key in BillingAddress.model_fields
                    }
                ),
                default_payment_method=default
                if isinstance(default, str)
                else getattr(default, "id", None),
                portal_enabled=bool(SETTINGS.STRIPE_PORTAL_CONFIGURATION_ID),
            )

    @observe_service("billing.update_profile")
    async def update_profile(
        self, user_id: int, form: BillingProfileForm
    ) -> BillingProfileResponse:
        async with self._provider() as client:
            customer_id = await self._customer(client, user_id)
            async with BillingCustomers.locked(user_id, self.config().livemode):
                await client.v1.customers.update_async(
                    customer_id,
                    params={
                        "email": form.email.strip(),
                        "name": form.name.strip(),
                        "address": form.address.model_dump(),
                    },
                    options={"idempotency_key": f"profile:{customer_id}:{form.request_id}"},
                )
        return await self.profile(user_id)

    @observe_service("billing.manage_method")
    async def manage_method(
        self, user_id: int, method_id: str, form: BillingMethodForm
    ) -> BillingProfileResponse:
        async with (
            self._provider() as client,
            BillingCustomers.locked(user_id, self.config().livemode) as row,
        ):
            if not row or not row.stripe_customer_id:
                raise BillingException(BillingErrorCode.BILLING_NOT_FOUND)
            method = await client.v1.payment_methods.retrieve_async(method_id)
            if (
                method.customer != row.stripe_customer_id
                or method.livemode != self.config().livemode
            ):
                raise BillingException(BillingErrorCode.BILLING_NOT_FOUND)
            customer = await client.v1.customers.retrieve_async(row.stripe_customer_id)
            subscriptions = await self._subscriptions(client, row.stripe_customer_id)
            if len(subscriptions) > 1:
                raise BillingException(BillingErrorCode.BILLING_RECONCILIATION_REQUIRED)
            default = getattr(customer.invoice_settings, "default_payment_method", None)
            active_default = (
                getattr(subscriptions[0], "default_payment_method", None) or default
                if subscriptions
                else None
            )
            prefix = f"method:{row.stripe_customer_id}:{form.request_id}"
            if form.action == "remove":
                if active_default == method_id or (subscriptions and not active_default):
                    raise BillingException(BillingErrorCode.BILLING_METHOD_REQUIRED)
                await client.v1.payment_methods.detach_async(
                    method_id, options={"idempotency_key": prefix + ":detach"}
                )
                if default == method_id:
                    await client.v1.customers.update_async(
                        row.stripe_customer_id,
                        params={"invoice_settings": {"default_payment_method": ""}},
                        options={"idempotency_key": prefix + ":clear"},
                    )
            else:
                if method.type not in ("card", "link"):
                    raise BillingException(BillingErrorCode.BILLING_NOT_FOUND)
                await client.v1.customers.update_async(
                    row.stripe_customer_id,
                    params={"invoice_settings": {"default_payment_method": method_id}},
                    options={"idempotency_key": prefix + ":customer"},
                )
                for subscription in subscriptions:
                    await client.v1.subscriptions.update_async(
                        subscription.id,
                        params={"default_payment_method": method_id},
                        options={"idempotency_key": prefix + ":subscription"},
                    )
        return await self.profile(user_id)

    @observe_service("billing.create_card_setup")
    async def create_card_setup(
        self, user_id: int, form: BillingSetupForm
    ) -> BillingCardSetupResponse:
        if not self.config().publishable_key:
            raise BillingException(BillingErrorCode.BILLING_PLAN_UNAVAILABLE)
        async with self._provider() as client:
            customer_id = await self._customer(client, user_id)
            intent = await client.v1.setup_intents.create_async(
                params={
                    "customer": customer_id,
                    "payment_method_types": ["card"],
                    "usage": "off_session",
                    "metadata": {"b4a_user_id": str(user_id)},
                },
                options={"idempotency_key": f"card-setup:{customer_id}:{form.request_id}"},
            )
            return BillingCardSetupResponse(id=intent.id, client_secret=intent.client_secret)

    @observe_service("billing.card_setup_status")
    async def card_setup_status(self, user_id: int, intent_id: str) -> BillingCardSetupStatus:
        async with self._provider() as client:
            row = await BillingCustomers.get(user_id, self.config().livemode)
            if not row or not row.stripe_customer_id:
                raise BillingException(BillingErrorCode.BILLING_NOT_FOUND)
            intent = await client.v1.setup_intents.retrieve_async(intent_id)
            if (
                intent.customer != row.stripe_customer_id
                or intent.livemode != self.config().livemode
            ):
                raise BillingException(BillingErrorCode.BILLING_NOT_FOUND)
            return BillingCardSetupStatus(
                registered=intent.status == "succeeded" and bool(intent.payment_method)
            )

    @staticmethod
    def _invoice_summary(item) -> BillingInvoiceResponse:
        return BillingInvoiceResponse(
            id=item.id,
            number=item.number,
            created=item.created,
            status=item.status or "draft",
            amount=item.amount_paid if item.status == "paid" else item.amount_due,
            currency=item.currency,
            url=item.hosted_invoice_url,
        )

    @observe_service("billing.invoices")
    async def invoices(
        self, user_id: int, limit: int = 4, starting_after: str | None = None
    ) -> BillingInvoicesResponse:
        async with self._provider() as client:
            row = await BillingCustomers.get(user_id, self.config().livemode)
            if not row or not row.stripe_customer_id:
                return BillingInvoicesResponse(items=[], has_more=False)
            params = {"customer": row.stripe_customer_id, "limit": limit}
            if starting_after:
                cursor = await client.v1.invoices.retrieve_async(starting_after)
                if (
                    cursor.customer != row.stripe_customer_id
                    or cursor.livemode != self.config().livemode
                ):
                    raise BillingException(BillingErrorCode.BILLING_NOT_FOUND)
                params["starting_after"] = starting_after
            invoices = await client.v1.invoices.list_async(params=params)
            return BillingInvoicesResponse(
                items=[self._invoice_summary(item) for item in invoices.data],
                has_more=invoices.has_more,
                next_cursor=invoices.data[-1].id if invoices.has_more and invoices.data else None,
            )

    @observe_service("billing.invoice_detail")
    async def invoice_detail(self, user_id: int, invoice_id: str) -> BillingInvoiceDetail:
        async with self._provider() as client:
            row = await BillingCustomers.get(user_id, self.config().livemode)
            if not row or not row.stripe_customer_id:
                raise BillingException(BillingErrorCode.BILLING_NOT_FOUND)
            item = await client.v1.invoices.retrieve_async(invoice_id)
            if item.customer != row.stripe_customer_id or item.livemode != self.config().livemode:
                raise BillingException(BillingErrorCode.BILLING_NOT_FOUND)
            return BillingInvoiceDetail(
                **self._invoice_summary(item).model_dump(),
                subtotal=item.subtotal,
                total=item.total,
                amount_paid=item.amount_paid,
                amount_due=item.amount_due,
                pdf_url=item.invoice_pdf,
                lines=[
                    BillingInvoiceLine(
                        description=line.description or "",
                        amount=line.amount,
                        quantity=line.quantity,
                    )
                    for line in item.lines.data
                ],
                lines_has_more=item.lines.has_more,
            )

    @observe_service("billing.portal")
    async def portal(self, user_id: int, form: BillingPortalForm) -> BillingSetupResponse:
        if not SETTINGS.STRIPE_PORTAL_CONFIGURATION_ID:
            raise BillingException(BillingErrorCode.BILLING_PLAN_UNAVAILABLE)
        async with self._provider() as client:
            # Restrict portal editing to profile/cards/invoices; plan policy stays in this service.
            config = await self._portal_configuration(client)
            customer_id = await self._customer(client, user_id)
            parts = urlsplit(SETTINGS.STRIPE_SETUP_CANCEL_URL)
            query = [
                (k, v)
                for k, v in parse_qsl(parts.query)
                if k not in ("billing_setup", "billing_checkout", "section")
            ]
            query.append(("section", "billing"))
            return_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))
            params = {"customer": customer_id, "configuration": config.id, "return_url": return_url}
            if form.flow == "payment_method_update":
                params["flow_data"] = {
                    "type": form.flow,
                    "after_completion": {
                        "type": "redirect",
                        "redirect": {"return_url": return_url},
                    },
                }
            session = await client.v1.billing_portal.sessions.create_async(
                params=params,
                options={"idempotency_key": f"billing-portal:{customer_id}:{form.request_id}"},
            )
            return BillingSetupResponse(id=session.id, url=session.url)

    async def _portal_configuration(self, client: stripe.StripeClient):
        config = await client.v1.billing_portal.configurations.retrieve_async(
            SETTINGS.STRIPE_PORTAL_CONFIGURATION_ID
        )
        features = config.features
        if (
            not config.active
            or config.livemode != self.config().livemode
            or features.subscription_cancel.enabled
            or features.subscription_update.enabled
            or not features.customer_update.enabled
            or not features.payment_method_update.enabled
            or not features.invoice_history.enabled
            or not {"email", "name", "address"}.issubset(features.customer_update.allowed_updates)
        ):
            raise BillingException(BillingErrorCode.BILLING_PLAN_UNAVAILABLE)
        return config
