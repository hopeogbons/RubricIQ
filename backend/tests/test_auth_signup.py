def test_signup_creates_inactive_viewer(client):
    response = client.post(
        "/auth/signup",
        json={"email": "new@user.com", "password": "hunter2-secret", "full_name": "New User"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "new@user.com"
    assert body["role"] == "viewer"
    assert body["is_active"] is False
    assert body["activated_at"] is None
    assert body["full_name"] == "New User"


def test_signup_duplicate_email_returns_400(client):
    payload = {"email": "dup@user.com", "password": "hunter2-secret"}
    client.post("/auth/signup", json=payload)
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_signup_short_password_rejected(client):
    response = client.post(
        "/auth/signup", json={"email": "short@user.com", "password": "abc"}
    )
    assert response.status_code == 422


def test_signup_invalid_email_rejected(client):
    response = client.post(
        "/auth/signup", json={"email": "not-an-email", "password": "hunter2-secret"}
    )
    assert response.status_code == 422
