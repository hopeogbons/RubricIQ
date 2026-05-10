import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.config import settings


def test_me_returns_current_user(client, auth_headers):
    headers, user = auth_headers(role="evaluator")
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["role"] == "evaluator"


def test_me_without_token_returns_401(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_with_expired_token_returns_401(client, make_user):
    user, _ = make_user(is_active=True)
    expired_payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "iat": int((datetime.now(tz=UTC) - timedelta(days=2)).timestamp()),
        "exp": int((datetime.now(tz=UTC) - timedelta(days=1)).timestamp()),
    }
    token = jwt.encode(expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_me_with_unknown_user_id_returns_401(client):
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "ghost@u.com",
        "role": "viewer",
        "iat": int(datetime.now(tz=UTC).timestamp()),
        "exp": int((datetime.now(tz=UTC) + timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_me_inactive_user_returns_403(client, auth_headers):
    headers, _ = auth_headers(role="viewer", is_active=False)
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 403
