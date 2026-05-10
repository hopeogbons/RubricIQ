from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.config import settings

ALGORITHM = "HS256"
DEFAULT_TTL_SECONDS = 2 * 60 * 60


def issue_callback_token(
    submission_id: UUID | str,
    *,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: datetime | None = None,
) -> str:
    """Sign the n8n callback token. n8n echoes this back in the callback body
    so we can verify the call originated from a workflow we triggered.

    Distinct secret from JWT_SECRET and ARTIFACT_SIGNING_SECRET so the three
    token surfaces (auth, artifact download, callback) are independent.
    """
    issued = now or datetime.now(tz=UTC)
    expires = issued + timedelta(seconds=ttl_seconds)
    payload = {
        "sub": str(submission_id),
        "iat": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(payload, settings.callback_secret, algorithm=ALGORITHM)


def decode_callback_token(token: str) -> UUID:
    """Verify signature + TTL and return the submission UUID claim."""
    payload = jwt.decode(token, settings.callback_secret, algorithms=[ALGORITHM])
    return UUID(payload["sub"])
