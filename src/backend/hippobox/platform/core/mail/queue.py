"""Authentication mail producers; SMTP execution belongs to standalone Celery."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from hippobox.platform.core.celery.publisher import publish_task
from hippobox.platform.core.config.settings import SETTINGS, Settings
from hippobox.platform.core.observability.logging import get_logger, mask_email

logger = get_logger("hippobox.platform.core.mail.queue")
MailKind = Literal[
    "signup_verification", "password_reset", "welcome", "account_deletion", "password_change"
]
MAIL_TASK_NAME = "b4fastapi.mail.send"


@dataclass
class MailQueueService:
    settings: Settings

    async def wake_lifecycle(self) -> None:
        """Wake the durable outbox without placing recipient data in the broker."""
        if self.settings.EMAIL_ENABLED:
            await publish_task("b4fastapi.notifications.drain", payload={})

    async def enqueue_signup_verification(
        self, *, to_email: str, user_name: str, link: str, language: str
    ) -> None:
        await self._enqueue(
            "signup_verification",
            to_email=to_email,
            user_name=user_name,
            link=link,
            language=language,
            ttl_minutes=self.settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES,
        )

    async def enqueue_password_reset(
        self, *, to_email: str, user_name: str, link: str, language: str
    ) -> None:
        await self._enqueue(
            "password_reset",
            to_email=to_email,
            user_name=user_name,
            link=link,
            language=language,
            ttl_minutes=self.settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
        )

    async def enqueue_welcome(self, *, to_email: str, user_name: str, language: str) -> None:
        await self._enqueue(
            "welcome",
            to_email=to_email,
            user_name=user_name,
            link=self.settings.APP_BASE_URL.rstrip("/") + "/",
            language=language,
            ttl_minutes=24 * 60,
        )

    async def enqueue_account_deletion(
        self, *, to_email: str, user_name: str, code: str, language: str
    ) -> None:
        await self._enqueue(
            "account_deletion",
            to_email=to_email,
            user_name=user_name,
            link="",
            code=code,
            language=language,
            ttl_minutes=10,
        )

    async def enqueue_password_change(
        self, *, to_email: str, user_name: str, code: str, language: str
    ) -> None:
        await self._enqueue(
            "password_change",
            to_email=to_email,
            user_name=user_name,
            link="",
            code=code,
            language=language,
            ttl_minutes=10,
        )

    async def _enqueue(
        self,
        kind: MailKind,
        *,
        to_email: str,
        user_name: str,
        link: str,
        language: str,
        ttl_minutes: int,
        code: str | None = None,
    ) -> None:
        if not self.settings.EMAIL_ENABLED:
            return
        now = datetime.now(UTC).timestamp()
        await publish_task(
            MAIL_TASK_NAME,
            payload={
                "message": {
                    "kind": kind,
                    **({"code": code} if kind in ("account_deletion", "password_change") else {}),
                    "to_email": to_email,
                    "user_name": user_name,
                    "link": link,
                    "language": language,
                    "created_at": now,
                    "expires_at": now + ttl_minutes * 60,
                }
            },
        )
        logger.info("Email job queued (type=%s, to=%s).", kind, mask_email(to_email))


MAIL_QUEUE_SERVICE = MailQueueService(SETTINGS)
