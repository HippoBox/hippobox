"""Mail provider, service, and template helpers."""

from hippobox.platform.core.mail.service import (
    MAIL_SERVICE,
    MailMessage,
    MailProvider,
    MailService,
    NullMailProvider,
    SMTPMailProvider,
)

__all__ = [
    "MAIL_SERVICE",
    "MailMessage",
    "MailProvider",
    "MailService",
    "NullMailProvider",
    "SMTPMailProvider",
]
