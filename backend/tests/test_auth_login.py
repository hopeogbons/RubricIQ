from app.services.auth_service import decode_access_token


def test_login_success_returns_decodable_jwt(client, make_user):
    user, password = make_user(role="evaluator", is_active=True, email="login@u.com")
    response = client.post(
        "/auth/login", json={"email": user.email, "password": password}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    payload = decode_access_token(body["access_token"])
    assert payload["sub"] == str(user.id)
    assert payload["role"] == "evaluator"


def test_login_inactive_user_returns_403(client, make_user):
    user, password = make_user(is_active=False, email="inactive@u.com")
    response = client.post(
        "/auth/login", json={"email": user.email, "password": password}
    )
    assert response.status_code == 403
    assert "not active" in response.json()["detail"].lower()


def test_login_wrong_password_returns_401(client, make_user):
    user, _ = make_user(is_active=True, email="wrongpw@u.com")
    response = client.post(
        "/auth/login", json={"email": user.email, "password": "incorrect"}
    )
    assert response.status_code == 401


def test_login_unknown_email_returns_401(client):
    response = client.post(
        "/auth/login", json={"email": "ghost@nowhere.com", "password": "whatever"}
    )
    assert response.status_code == 401


def test_login_rate_limit_returns_429_after_five_attempts(client, make_user):
    user, password = make_user(is_active=True, email="rate@u.com")
    creds = {"email": user.email, "password": password}
    for _ in range(5):
        r = client.post("/auth/login", json=creds)
        assert r.status_code == 200
    over = client.post("/auth/login", json=creds)
    assert over.status_code == 429
