import logging
from functools import lru_cache
from typing import Any, Protocol

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class N8nTriggerError(Exception):
    """Raised when the n8n webhook cannot be reached or returns non-2xx."""


class N8nClient(Protocol):
    def trigger(self, payload: dict[str, Any]) -> None: ...


class HttpN8nClient:
    def __init__(
        self, webhook_url: str, secret: str | None, *, timeout_s: float = 30.0
    ) -> None:
        self._url = webhook_url
        self._secret = secret
        self._timeout = timeout_s

    def trigger(self, payload: dict[str, Any]) -> None:
        headers = {"Content-Type": "application/json"}
        if self._secret:
            headers["X-API-Key"] = self._secret
        try:
            response = httpx.post(
                self._url, json=payload, headers=headers, timeout=self._timeout
            )
        except httpx.HTTPError as exc:
            raise N8nTriggerError(f"n8n transport error: {exc}") from exc

        if response.status_code >= 400:
            raise N8nTriggerError(
                f"n8n returned {response.status_code}: {response.text[:200]}"
            )


class DisabledN8nClient:
    """Used when N8N_WEBHOOK_URL is not configured; surfaces a clean error
    rather than masking a misconfiguration."""

    def trigger(self, payload: dict[str, Any]) -> None:
        raise N8nTriggerError(
            "n8n webhook is not configured (set N8N_WEBHOOK_URL)"
        )


@lru_cache(maxsize=1)
def get_n8n_client() -> N8nClient:
    if settings.n8n_webhook_url:
        return HttpN8nClient(settings.n8n_webhook_url, settings.n8n_webhook_secret)
    return DisabledN8nClient()
