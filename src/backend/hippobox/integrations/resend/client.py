import logging
from typing import Iterable

import httpx

from hippobox.core.settings import SETTINGS

log = logging.getLogger("email")

DEFAULT_TIMEOUT_SECONDS = 10.0


class ResendClient:
    def __init__(self):
        self._api_key = SETTINGS.RESEND_API_KEY
        self._base_url = SETTINGS.RESEND_API_BASE_URL
        self._from = SETTINGS.EMAIL_FROM
        self._reply_to = SETTINGS.EMAIL_REPLY_TO or None

    def _is_configured(self) -> bool:
        return bool(self._api_key and self._from)

    async def send_email(
        self,
        *,
        to: Iterable[str],
        subject: str,
        html: str,
        text: str,
        idempotency_key: str | None = None,
        reply_to: str | None = None,
    ) -> str | None:
        if not self._is_configured():
            log.warning("Resend not configured. Set RESEND_API_KEY and EMAIL_FROM to enable email sending.")
            return None

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        payload = {
            "from": self._from,
            "to": list(to),
            "subject": subject,
            "html": html,
            "text": text,
        }

        reply_value = reply_to or self._reply_to
        if reply_value:
            payload["replyTo"] = reply_value

        async with httpx.AsyncClient(base_url=self._base_url, timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.post("/emails", json=payload, headers=headers)

        if response.status_code >= 300:
            log.warning("Resend send failed (%s): %s", response.status_code, response.text)
            return None

        try:
            data = response.json()
        except ValueError:
            log.warning("Resend send succeeded but returned non-JSON response.")
            return None

        return data.get("id")
