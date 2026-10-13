"""Bounded SMTP retries and idempotent failed-mail archival."""

import asyncio
import json
from datetime import UTC, datetime

from celery import Task
from celery.signals import worker_init
from pydantic import BaseModel, Field, FiniteFloat, ValidationError, model_validator
from redis import Redis
from redis.exceptions import RedisError

from hippobox.platform.core.celery.app import celery_app
from hippobox.platform.core.config.settings import SETTINGS
from hippobox.platform.core.mail.queue import MAIL_TASK_NAME, MailKind
from hippobox.platform.core.mail.service import MAIL_SERVICE
from hippobox.platform.core.observability.logging import get_logger
from hippobox.platform.core.observability.task_context import get_task_context

logger = get_logger("hippobox.platform.core.celery.mail")


class MailJob(BaseModel):
    kind: MailKind
    to_email: str = Field(min_length=1)
    user_name: str
    link: str = ""
    code: str | None = Field(default=None, pattern=r"^[0-9]{6}$")
    language: str
    created_at: FiniteFloat
    expires_at: FiniteFloat

    @model_validator(mode="after")
    def validate_content(self) -> "MailJob":
        if self.kind in ("account_deletion", "password_change"):
            if self.code is None:
                raise ValueError("Missing verification code")
        elif not self.link:
            raise ValueError("Missing mail link")
        return self


def archive_failure(*, task_id: str, record: dict[str, object]) -> None:
    """Repeated archival overwrites one record instead of appending duplicates."""
    with Redis.from_url(
        SETTINGS.celery_broker_url, socket_connect_timeout=5, socket_timeout=5
    ) as client:
        client.hset(
            f"{SETTINGS.CELERY_KEY_PREFIX}mail:failures",
            task_id,
            json.dumps(record, separators=(",", ":")),
        )


def _archive_or_retry(
    task: Task,
    *,
    message: dict[str, object],
    delivery_attempt: int,
    reason: str,
) -> None:
    task_id, trace_id = get_task_context()
    try:
        archive_failure(
            task_id=task_id,
            record={
                "task_id": task_id,
                "trace_id": trace_id,
                "message": message,
                "delivery_attempt": delivery_attempt,
                "reason": reason,
                "failed_at": datetime.now(UTC).isoformat(),
            },
        )
    except (RedisError, OSError):
        logger.warning("Mail failure archive unavailable; retrying archival only.")
        # This phase never invokes SMTP again. A broker publish failure causes
        # Celery Retry to reject/requeue the original unacknowledged delivery.
        raise task.retry(
            kwargs={
                "message": message,
                "delivery_attempt": delivery_attempt,
                "failure_reason": reason,
            },
            countdown=60,
            max_retries=None,
            kwargsrepr="<redacted>",
        ) from None
    logger.error("Mail job archived (reason=%s, attempt=%s).", reason, delivery_attempt)


@celery_app.task(bind=True, name=MAIL_TASK_NAME, max_retries=None)
def send_mail(
    self: Task,
    *,
    message: dict[str, object],
    delivery_attempt: int = 0,
    failure_reason: str | None = None,
) -> None:
    if failure_reason is not None:
        _archive_or_retry(
            self, message=message, delivery_attempt=delivery_attempt, reason=failure_reason
        )
        return
    if not SETTINGS.EMAIL_ENABLED:
        logger.info("Email job skipped because email integration is disabled.")
        return
    try:
        job = MailJob.model_validate(message)
    except ValidationError:
        _archive_or_retry(
            self, message=message, delivery_attempt=delivery_attempt, reason="invalid_payload"
        )
        return
    if job.expires_at <= datetime.now(UTC).timestamp():
        _archive_or_retry(
            self, message=message, delivery_attempt=delivery_attempt, reason="expired"
        )
        return
    sender = {
        "signup_verification": MAIL_SERVICE.send_signup_verification_email,
        "password_reset": MAIL_SERVICE.send_password_reset_email,
        "welcome": MAIL_SERVICE.send_welcome_email,
        "account_deletion": MAIL_SERVICE.send_account_deletion_email,
        "password_change": MAIL_SERVICE.send_password_change_email,
    }[job.kind]
    try:
        asyncio.run(
            sender(
                to_email=job.to_email,
                user_name=job.user_name,
                **(
                    {"code": job.code}
                    if job.kind in ("account_deletion", "password_change")
                    else {"link": job.link}
                ),
                language=job.language,
                raise_on_failure=True,
            )
        )
    except Exception as error:
        if delivery_attempt < max(0, SETTINGS.EMAIL_QUEUE_MAX_RETRIES):
            logger.warning("Mail delivery retry scheduled (attempt=%s).", delivery_attempt + 1)
            raise self.retry(
                kwargs={"message": message, "delivery_attempt": delivery_attempt + 1},
                countdown=max(0, SETTINGS.EMAIL_QUEUE_RETRY_DELAY_SECONDS),
                kwargsrepr="<redacted>",
            ) from None
        _archive_or_retry(
            self,
            message=message,
            delivery_attempt=delivery_attempt,
            reason=type(error).__name__,
        )


@worker_init.connect
def initialize_mail_worker(**kwargs: object) -> None:
    """Validate SMTP once before worker pool creation, not inside each task."""
    try:
        asyncio.run(MAIL_SERVICE.initialize())
    except Exception as error:
        raise SystemExit("Celery mail worker SMTP initialization failed.") from error
