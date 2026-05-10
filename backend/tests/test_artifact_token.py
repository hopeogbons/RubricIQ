import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import settings
from app.services.artifact_token import (
    ALGORITHM,
    decode_artifact_token,
    issue_artifact_token,
)


def test_round_trip():
    sub = uuid.uuid4()
    token = issue_artifact_token(sub, "demo.mp4")
    decoded_sub, fn = decode_artifact_token(token)
    assert decoded_sub == sub
    assert fn == "demo.mp4"


def test_expired_token_raises():
    past = datetime.now(tz=UTC) - timedelta(hours=3)
    sub = uuid.uuid4()
    token = issue_artifact_token(sub, "x.png", ttl_seconds=60, now=past)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_artifact_token(token)


def test_tampered_signature_raises():
    sub = uuid.uuid4()
    token = issue_artifact_token(sub, "x.png")
    head, payload, _sig = token.split(".")
    tampered = f"{head}.{payload}.AAAA"
    with pytest.raises(jwt.PyJWTError):
        decode_artifact_token(tampered)


def test_wrong_secret_does_not_validate():
    sub = uuid.uuid4()
    token = issue_artifact_token(sub, "x.png")
    with pytest.raises(jwt.PyJWTError):
        jwt.decode(token, "different-but-also-32-bytes-long-secret-xx", algorithms=[ALGORITHM])


def test_decode_uses_artifact_secret_not_jwt_secret():
    """Artifact tokens must NOT validate under JWT_SECRET (separate keys)."""
    sub = uuid.uuid4()
    token = issue_artifact_token(sub, "x.png")
    with pytest.raises(jwt.PyJWTError):
        jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
