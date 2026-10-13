import asyncio
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from urllib.parse import urljoin

from hippobox.platform.core.config.settings import SETTINGS, Settings
from hippobox.platform.core.mail.templates import (
    build_account_deletion_email,
    build_password_change_email,
    build_password_reset_email,
    build_verification_email,
    build_welcome_email,
)
from hippobox.platform.core.observability.logging import get_logger, mask_email

logger = get_logger("hippobox.platform.mail")


@dataclass(frozen=True)
class MailMessage:
    to_email: str
    subject: str
    text_body: str
    html_body: str | None = None


class MailProvider:
    def validate_configuration(self) -> None:
        raise NotImplementedError

    def verify_startup(self) -> None:
        raise NotImplementedError

    async def send(self, message: MailMessage) -> None:
        raise NotImplementedError


class NullMailProvider(MailProvider):
    def validate_configuration(self) -> None:
        return

    def verify_startup(self) -> None:
        return

    async def send(self, message: MailMessage) -> None:
        logger.info("Email disabled. Skip sending email to %s.", mask_email(message.to_email))


class SMTPMailProvider(MailProvider):
    def __init__(self, settings: Settings):
        self._settings = settings

    def validate_configuration(self) -> None:
        errors = self._settings.get_smtp_validation_errors()
        if errors:
            raise ValueError("; ".join(errors))

    def verify_startup(self) -> None:
        with self._open_client():
            return

    async def send(self, message: MailMessage) -> None:
        await asyncio.to_thread(self._send_sync, message)

    def _send_sync(self, message: MailMessage) -> None:
        with self._open_client() as smtp:
            smtp.send_message(self._build_email_message(message))

    def _build_email_message(self, message: MailMessage) -> EmailMessage:
        email_message = EmailMessage()
        email_message["Subject"] = message.subject
        email_message["From"] = self._settings.EMAIL_FROM
        email_message["To"] = message.to_email
        email_message.set_content(message.text_body)
        if message.html_body:
            email_message.add_alternative(message.html_body, subtype="html")
        return email_message

    def _open_client(self) -> smtplib.SMTP:
        smtp_factory = smtplib.SMTP_SSL if self._settings.SMTP_USE_SSL else smtplib.SMTP
        smtp = smtp_factory(
            host=self._settings.SMTP_HOST,
            port=self._settings.SMTP_PORT,
            timeout=self._settings.SMTP_TIMEOUT_SECONDS,
        )
        try:
            smtp.ehlo()
            if self._settings.SMTP_USE_STARTTLS and not self._settings.SMTP_USE_SSL:
                smtp.starttls()
                smtp.ehlo()

            if self._settings.SMTP_USERNAME and self._settings.SMTP_PASSWORD:
                smtp.login(self._settings.SMTP_USERNAME, self._settings.SMTP_PASSWORD)
        except BaseException:
            smtp.close()
            raise
        return smtp


class MailService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._provider: MailProvider = (
            SMTPMailProvider(settings) if settings.EMAIL_ENABLED else NullMailProvider()
        )

    async def initialize(self) -> None:
        if not self._settings.EMAIL_ENABLED:
            logger.info("Email integration is disabled.")
            return

        try:
            self._provider.validate_configuration()
        except ValueError:
            logger.exception("SMTP configuration validation failed.")
            raise

        logger.info(
            "SMTP integration enabled (host=%s, port=%s, starttls=%s, ssl=%s).",
            self._settings.SMTP_HOST,
            self._settings.SMTP_PORT,
            self._settings.SMTP_USE_STARTTLS,
            self._settings.SMTP_USE_SSL,
        )

        if self._settings.SMTP_VALIDATE_ON_STARTUP:
            await asyncio.to_thread(self._provider.verify_startup)
            logger.info("SMTP startup verification succeeded.")
        else:
            logger.info("SMTP startup verification skipped by configuration.")

    async def check_connection(self) -> None:
        """Authenticate without sending mail; keep probe socket waits short."""
        if not self._settings.EMAIL_ENABLED:
            return
        settings = self._settings.model_copy(update={"SMTP_TIMEOUT_SECONDS": 2})
        provider = SMTPMailProvider(settings)
        provider.validate_configuration()
        await asyncio.to_thread(provider.verify_startup)

    async def send_signup_verification_email(
        self,
        *,
        to_email: str,
        user_name: str,
        link: str = "",
        language: str | None = None,
        raise_on_failure: bool = False,
    ) -> None:
        if not self._settings.EMAIL_ENABLED:
            return
        resolved_link = self._resolve_link(path="/verify-email", link=link)
        if not resolved_link:
            logger.warning("Skip signup verification email. Missing APP_BASE_URL and link.")
            return

        content = build_verification_email(
            name=user_name,
            link=resolved_link,
            app_name=self._settings.EMAIL_BRAND_NAME,
            language=language,
        )
        message = MailMessage(
            to_email=to_email,
            subject=content.subject,
            text_body=content.text,
            html_body=content.html,
        )
        logger.debug("Attempting signup verification email delivery to %s.", mask_email(to_email))
        try:
            await self._provider.send(message)
            logger.info("Signup verification email delivered to %s.", mask_email(to_email))
        except Exception:
            if raise_on_failure:
                raise
            logger.exception(
                "Failed to send signup verification email to %s.", mask_email(to_email)
            )

    async def send_password_reset_email(
        self,
        *,
        to_email: str,
        user_name: str,
        link: str = "",
        language: str | None = None,
        raise_on_failure: bool = False,
    ) -> None:
        if not self._settings.EMAIL_ENABLED:
            return
        resolved_link = self._resolve_link(path="/reset-password", link=link)
        if not resolved_link:
            logger.warning("Skip password reset email. Missing APP_BASE_URL and link.")
            return

        content = build_password_reset_email(
            name=user_name,
            link=resolved_link,
            app_name=self._settings.EMAIL_BRAND_NAME,
            language=language,
        )
        message = MailMessage(
            to_email=to_email,
            subject=content.subject,
            text_body=content.text,
            html_body=content.html,
        )
        logger.debug("Attempting password reset email delivery to %s.", mask_email(to_email))
        try:
            await self._provider.send(message)
            logger.info("Password reset email delivered to %s.", mask_email(to_email))
        except Exception:
            if raise_on_failure:
                raise
            logger.exception("Failed to send password reset email to %s.", mask_email(to_email))

    async def send_welcome_email(
        self,
        *,
        to_email: str,
        user_name: str,
        link: str = "",
        language: str | None = None,
        raise_on_failure: bool = False,
    ) -> None:
        if not self._settings.EMAIL_ENABLED:
            return
        content = build_welcome_email(
            name=user_name,
            link=self._resolve_link(path="/", link=link),
            app_name=self._settings.EMAIL_BRAND_NAME,
            language=language,
        )
        try:
            await self._provider.send(
                MailMessage(
                    to_email=to_email,
                    subject=content.subject,
                    text_body=content.text,
                    html_body=content.html,
                )
            )
            logger.info("Welcome email delivered to %s.", mask_email(to_email))
        except Exception:
            if raise_on_failure:
                raise
            logger.exception("Failed to send welcome email to %s.", mask_email(to_email))

    async def send_account_deletion_email(
        self,
        *,
        to_email: str,
        user_name: str,
        code: str,
        language: str | None = None,
        raise_on_failure: bool = False,
    ) -> None:
        if not self._settings.EMAIL_ENABLED:
            return
        content = build_account_deletion_email(
            name=user_name,
            code=code,
            app_name=self._settings.EMAIL_BRAND_NAME,
            language=language,
        )
        try:
            await self._provider.send(
                MailMessage(
                    to_email=to_email,
                    subject=content.subject,
                    text_body=content.text,
                    html_body=content.html,
                )
            )
            logger.info("Account deletion code delivered to %s.", mask_email(to_email))
        except Exception:
            if raise_on_failure:
                raise
            logger.exception("Failed to deliver account deletion code to %s.", mask_email(to_email))

    async def send_password_change_email(
        self,
        *,
        to_email: str,
        user_name: str,
        code: str,
        language: str | None = None,
        raise_on_failure: bool = False,
    ) -> None:
        if not self._settings.EMAIL_ENABLED:
            return
        content = build_password_change_email(
            name=user_name,
            code=code,
            app_name=self._settings.EMAIL_BRAND_NAME,
            language=language,
        )
        try:
            await self._provider.send(
                MailMessage(
                    to_email=to_email,
                    subject=content.subject,
                    text_body=content.text,
                    html_body=content.html,
                )
            )
            logger.info("Password change code delivered to %s.", mask_email(to_email))
        except Exception:
            if raise_on_failure:
                raise
            logger.exception("Failed to deliver password change code to %s.", mask_email(to_email))

    async def send_lifecycle_email(
        self, *, kind: str, email: str, name: str, language: str, plan: str
    ) -> None:
        from hippobox.platform.core.mail.templates import build_lifecycle_email

        if not self._settings.EMAIL_ENABLED:
            return
        content = build_lifecycle_email(
            kind=kind,
            name=name,
            plan=plan,
            language=language,
            app_name=self._settings.EMAIL_BRAND_NAME,
            link=self._settings.APP_BASE_URL.rstrip("/")
            + ("/home" if kind == "account_deleted" else "/settings?section=billing"),
        )
        await self._provider.send(
            MailMessage(
                to_email=email,
                subject=content.subject,
                text_body=content.text,
                html_body=content.html,
            )
        )

    def _resolve_link(self, *, path: str, link: str) -> str:
        explicit_link = link.strip()
        if explicit_link:
            return explicit_link

        base_url = self._settings.APP_BASE_URL.strip()
        if not base_url:
            return ""

        normalized_base = f"{base_url.rstrip('/')}/"
        return urljoin(normalized_base, path.lstrip("/"))


MAIL_SERVICE = MailService(SETTINGS)
