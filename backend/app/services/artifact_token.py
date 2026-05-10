from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.config import settings

ALGORITHM = "HS256"
DEFAULT_TTL_SECONDS = 2 * 60 * 60


def issue_artifact_token(
    submission_id: UUID | str,
    filename: str,
    *,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: datetime | None = None,
) -> str:
    """Sign a short-lived URL token n8n uses to download an artifact.

    Distinct secret from the auth JWT_SECRET so leaking auth tokens cannot mint
    artifact URLs (and vice versa).
    """
    issued = now or datetime.now(tz=UTC)
    expires = issued + timedelta(seconds=ttl_seconds)
    payload = {
        "sub": str(submission_id),
        "fn": filename,
        "iat": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(payload, settings.artifact_signing_secret, algorithm=ALGORITHM)


def decode_artifact_token(token: str) -> tuple[UUID, str]:
    """Verify the token signature and TTL, return (submission_id, filename).

    Raises jwt.PyJWTError subclasses on bad/expired tokens, ValueError if the
    submission_id claim isn't a UUID.
    """
    payload = jwt.decode(token, settings.artifact_signing_secret, algorithms=[ALGORITHM])
    submission_id = UUID(payload["sub"])
    filename = payload["fn"]
    if not isinstance(filename, str) or not filename:
        raise ValueError("artifact token missing filename")
    return submission_id, filename
