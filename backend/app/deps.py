from collections.abc import Callable, Iterable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.services.auth_service import decode_access_token, get_user_from_token_payload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise _CREDENTIALS_EXC
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.PyJWTError as exc:
        raise _CREDENTIALS_EXC from exc

    user = get_user_from_token_payload(db, payload)
    if user is None:
        raise _CREDENTIALS_EXC
    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account not active"
        )
    return user


def require_roles(*roles: str) -> Callable[[User], User]:
    allowed: frozenset[str] = frozenset(roles)

    def _dep(user: User = Depends(get_current_active_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _dep


require_admin = require_roles("admin", "superadmin")
require_superadmin = require_roles("superadmin")
require_admin_or_evaluator = require_roles("admin", "superadmin", "evaluator")


__all__: Iterable[str] = [
    "get_db",
    "oauth2_scheme",
    "get_current_user",
    "get_current_active_user",
    "require_roles",
    "require_admin",
    "require_superadmin",
    "require_admin_or_evaluator",
]
