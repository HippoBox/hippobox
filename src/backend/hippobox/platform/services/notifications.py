"""Lifecycle event -> encrypted outbox -> bounded SMTP delivery."""

import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Literal

from cryptography.fernet import Fernet

from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.mail.queue import MAIL_QUEUE_SERVICE
from hippobox.platform.core.mail.service import MAIL_SERVICE
from hippobox.platform.core.observability.logging import get_logger
from hippobox.platform.models.notification import MAX_DELIVERY_ATTEMPTS, Notification, Notifications

logger = get_logger("hippobox.platform.service.notifications")
NotificationKind = Literal["subscription_started", "plan_changed", "account_deleted"]


def cipher() -> Fernet:
    return Fernet(
        base64.urlsafe_b64encode(
            hashlib.sha256(b"mail-notification-v1:" + SETTINGS.SECRET_KEY.encode()).digest()
        )
    )


def notification_row(
    key: str, kind: NotificationKind, *, email: str, name: str, language: str = "en", plan: str = ""
) -> Notification:
    now = datetime.now(UTC)
    recipient = dict(email=email, language=language)
    if kind != "account_deleted":
        recipient.update(name=name, plan=plan)
    payload = cipher().encrypt(json.dumps(recipient).encode()).decode()
    return Notification(
        id=hashlib.sha256(key.encode()).hexdigest(),
        kind=kind,
        payload=payload,
        state="pending",
        attempts=0,
        available_at=now,
        expires_at=now + timedelta(hours=72),
    )


async def wake_notifications() -> None:
    try:
        await MAIL_QUEUE_SERVICE.wake_lifecycle()
    except Exception:
        # Beat will recover; do not undo the committed domain result.
        logger.warning("Notification wake-up unavailable; durable outbox retained.")


async def queue_notification(
    key: str, kind: NotificationKind, *, previous_key: str | None = None, **payload: str
) -> None:
    if not SETTINGS.EMAIL_ENABLED:
        return
    if previous_key and await Notifications.exists(
        hashlib.sha256(previous_key.encode()).hexdigest()
    ):
        return
    await Notifications.add(notification_row(key, kind, **payload))
    await wake_notifications()


async def deliver_notifications() -> None:
    for _ in range(10):
        row = await Notifications.claim()
        if row is None:
            return
        if not SETTINGS.EMAIL_ENABLED or (
            row.kind != "account_deleted" and not SETTINGS.STRIPE_ENABLED
        ):
            await Notifications.finish(row, state="skipped")
            continue
        try:
            payload = json.loads(cipher().decrypt(row.payload.encode()))
            payload.setdefault("name", "")
            payload.setdefault("plan", "")
            await MAIL_SERVICE.send_lifecycle_email(kind=row.kind, **payload)
        except Exception:
            await Notifications.finish(
                row,
                state="pending" if row.attempts < MAX_DELIVERY_ATTEMPTS else "failed",
                error="delivery_failed",
            )
            logger.warning(
                "Lifecycle mail delivery failed (id=%s, attempt=%s).", row.id, row.attempts
            )
        else:
            await Notifications.finish(row, state="sent")
