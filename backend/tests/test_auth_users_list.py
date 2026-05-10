def test_admin_lists_users(client, auth_headers, make_user):
    headers, _ = auth_headers(role="admin")
    make_user(email="a@u.com")
    make_user(email="b@u.com")
    response = client.get("/auth/users", headers=headers)
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()}
    assert "a@u.com" in emails
    assert "b@u.com" in emails


def test_superadmin_lists_users(client, auth_headers):
    headers, _ = auth_headers(role="superadmin")
    response = client.get("/auth/users", headers=headers)
    assert response.status_code == 200


def test_evaluator_cannot_list_users(client, auth_headers):
    headers, _ = auth_headers(role="evaluator")
    response = client.get("/auth/users", headers=headers)
    assert response.status_code == 403


def test_viewer_cannot_list_users(client, auth_headers):
    headers, _ = auth_headers(role="viewer")
    response = client.get("/auth/users", headers=headers)
    assert response.status_code == 403


def test_unauthenticated_cannot_list_users(client):
    response = client.get("/auth/users")
    assert response.status_code == 401
