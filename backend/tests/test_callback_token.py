import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import settings
from app.services.callback_token import (
    ALGORITHM,
    decode_callback_token,
    issue_callback_token,
)


def test_round_trip():
    sub = uuid.uuid4()
    token = issue_callback_token(sub)
    assert decode_callback_token(token) == sub


def test_expired_token_raises():
    past = datetime.now(tz=UTC) - timedelta(hours=3)
    sub = uuid.uuid4()
    token = issue_callback_token(sub, ttl_seconds=60, now=past)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_callback_token(token)


def test_tampered_signature_raises():
    sub = uuid.uuid4()
    token = issue_callback_token(sub)
    head, payload, _sig = token.split(".")
    with pytest.raises(jwt.PyJWTError):
        decode_callback_token(f"{head}.{payload}.AAAA")


def test_callback_token_does_not_validate_under_jwt_secret():
    sub = uuid.uuid4()
    token = issue_callback_token(sub)
    with pytest.raises(jwt.PyJWTError):
        jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


def test_callback_token_does_not_validate_under_artifact_secret():
    sub = uuid.uuid4()
    token = issue_callback_token(sub)
    with pytest.raises(jwt.PyJWTError):
        jwt.decode(token, settings.artifact_signing_secret, algorithms=[ALGORITHM])
