import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, settings
from app.models import User

logger = logging.getLogger(__name__)

# bcrypt rejects inputs longer than 72 bytes; truncate so multi-byte UTF-8 passwords
# whose char count is within the schema limit don't trip on the byte limit.
_BCRYPT_MAX_BYTES = 72


def hash_password(plain: str) -> str:
    secret = plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(secret, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8")[:_BCRYPT_MAX_BYTES], hashed.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def create_access_token(user: User, *, now: datetime | None = None) -> str:
    issued = now or datetime.now(tz=UTC)
    expires = issued + timedelta(minutes=settings.jwt_expires_minutes)
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "iat": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def get_user_from_token_payload(db: Session, payload: dict[str, Any]) -> User | None:
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        user_id = UUID(sub)
    except (TypeError, ValueError):
        return None
    return db.get(User, user_id)


def seed_superadmin(db: Session, cfg: Settings) -> User | None:
    """Idempotently ensure a superadmin exists.

    Returns the seeded user if one was created, None if a superadmin already existed.
    Raises RuntimeError when no superadmin exists and the seed env vars are missing,
    so a misconfigured production deploy fails to boot rather than running admin-less.
    """
    existing = db.scalar(select(User).where(User.role == "superadmin").limit(1))
    if existing is not None:
        return None

    if not cfg.superadmin_email or not cfg.superadmin_password:
        raise RuntimeError(
            "No superadmin exists and SUPERADMIN_EMAIL/SUPERADMIN_PASSWORD are not set. "
            "Set them on first boot to seed the initial superadmin."
        )

    user = User(
        email=cfg.superadmin_email,
        password_hash=hash_password(cfg.superadmin_password),
        full_name="Superadmin",
        role="superadmin",
        is_active=True,
        activated_at=datetime.now(tz=UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Seeded superadmin %s", user.email)
    return user
