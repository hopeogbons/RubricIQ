import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import get_current_active_user, get_db, require_admin
from app.models import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserOut
from app.services.auth_service import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.services.email_service import (
    EmailClient,
    EmailSendError,
    get_email_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Per-IP rate limiter; only attached to /login per SPEC.
limiter = Limiter(key_func=get_remote_address)


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: Session = Depends(get_db)) -> User:
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="viewer",
        is_active=False,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        ) from exc
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == body.email))
    # Uniform 401 for unknown email and bad password to avoid user enumeration.
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account not active"
        )
    return TokenResponse(access_token=create_access_token(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_active_user)) -> User:
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(
    _admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


@router.post("/users/{user_id}/activate", response_model=UserOut)
def activate_user(
    user_id: UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    email_client: EmailClient = Depends(get_email_client),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.is_active:
        return user

    user.is_active = True
    user.activated_at = datetime.now(tz=UTC)
    db.commit()
    db.refresh(user)

    from app.config import settings  # late import keeps test overrides simple

    login_url = f"{settings.frontend_base_url.rstrip('/')}/login"
    try:
        email_client.send_activation(
            to=user.email, full_name=user.full_name, login_url=login_url
        )
    except EmailSendError:
        logger.warning(
            "Activation email send failed for user_id=%s email=%s; activation kept",
            user.id,
            user.email,
            exc_info=True,
        )
    return user
