import logging
from functools import lru_cache
from typing import Protocol

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

RESEND_ENDPOINT = "https://api.resend.com/emails"


class EmailSendError(Exception):
    """Raised when an email cannot be delivered (transport or 4xx/5xx response)."""


class EmailClient(Protocol):
    def send_activation(
        self, *, to: str, full_name: str | None, login_url: str
    ) -> None: ...


class NoopEmailClient:
    def send_activation(
        self, *, to: str, full_name: str | None, login_url: str
    ) -> None:
        logger.info(
            "NoopEmailClient: would send activation email to %s (login_url=%s)",
            to,
            login_url,
        )


class ResendEmailClient:
    def __init__(self, api_key: str, from_email: str, *, timeout_s: float = 10.0) -> None:
        self._api_key = api_key
        self._from = from_email
        self._timeout = timeout_s

    def send_activation(
        self, *, to: str, full_name: str | None, login_url: str
    ) -> None:
        greeting = f"Hi {full_name}," if full_name else "Hi,"
        subject = "Your RubricIQ account is active"
        text_body = (
            f"{greeting}\n\n"
            "Your RubricIQ account has been activated. "
            f"You can now log in at {login_url}.\n\n"
            "RubricIQ"
        )
        html_body = (
            f"<p>{greeting}</p>"
            "<p>Your RubricIQ account has been activated. "
            f'You can now log in at <a href="{login_url}">{login_url}</a>.</p>'
            "<p>RubricIQ</p>"
        )
        payload = {
            "from": self._from,
            "to": [to],
            "subject": subject,
            "text": text_body,
            "html": html_body,
        }
        try:
            response = httpx.post(
                RESEND_ENDPOINT,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise EmailSendError(f"Resend transport error: {exc}") from exc

        if response.status_code >= 400:
            raise EmailSendError(
                f"Resend returned {response.status_code}: {response.text}"
            )


@lru_cache(maxsize=1)
def get_email_client() -> EmailClient:
    if settings.resend_api_key:
        return ResendEmailClient(settings.resend_api_key, settings.resend_from_email)
    return NoopEmailClient()
