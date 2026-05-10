import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import settings
from app.models import User
from app.services.auth_service import create_access_token, decode_access_token


def _user(role="viewer"):
    return User(
        id=uuid.uuid4(),
        email="x@y.com",
        password_hash="x",
        role=role,
        is_active=True,
    )


def test_round_trip_carries_sub_role_email():
    token = create_access_token(_user(role="admin"))
    payload = decode_access_token(token)
    assert payload["role"] == "admin"
    assert payload["email"] == "x@y.com"
    assert payload["sub"]
    assert "exp" in payload and "iat" in payload


def test_expired_token_raises():
    past = datetime.now(tz=UTC) - timedelta(hours=2)
    token = create_access_token(_user(), now=past - timedelta(minutes=settings.jwt_expires_minutes))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_tampered_signature_raises():
    token = create_access_token(_user())
    head, payload, _sig = token.split(".")
    tampered = f"{head}.{payload}.AAAA"
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(tampered)


def test_wrong_secret_raises():
    token = create_access_token(_user())
    with pytest.raises(jwt.PyJWTError):
        jwt.decode(
            token,
            "different-secret-also-32-bytes-long-for-hs256",
            algorithms=[settings.jwt_algorithm],
        )
