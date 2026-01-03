import logging

from hippobox.core.email_links import build_password_reset_link, build_verify_email_link
from hippobox.core.email_templates import build_password_reset_email, build_verification_email
from hippobox.integrations.resend.client import ResendClient

log = logging.getLogger("email")


def _idempotency_key(prefix: str, token: str) -> str:
    return f"{prefix}:{token}"


async def send_verification_email(*, email: str, name: str | None, token: str) -> str | None:
    link = build_verify_email_link(token)
    content = build_verification_email(name=name, link=link)
    client = ResendClient()
    message_id = await client.send_email(
        to=[email],
        subject=content.subject,
        html=content.html,
        text=content.text,
        idempotency_key=_idempotency_key("verify-email", token),
    )
    if message_id:
        log.info("Verification email sent to %s (id=%s)", email, message_id)
    return message_id


async def send_password_reset_email(*, email: str, name: str | None, token: str) -> str | None:
    link = build_password_reset_link(token)
    content = build_password_reset_email(name=name, link=link)
    client = ResendClient()
    message_id = await client.send_email(
        to=[email],
        subject=content.subject,
        html=content.html,
        text=content.text,
        idempotency_key=_idempotency_key("reset-password", token),
    )
    if message_id:
        log.info("Password reset email sent to %s (id=%s)", email, message_id)
    return message_id
