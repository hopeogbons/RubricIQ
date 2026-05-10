import uuid

from app.services.email_service import EmailSendError


def test_admin_activates_user_and_email_sent(
    client, auth_headers, make_user, recording_email_client
):
    headers, _ = auth_headers(role="admin")
    target, _ = make_user(role="viewer", is_active=False, email="target@u.com", full_name="Tee")

    response = client.post(f"/auth/users/{target.id}/activate", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_active"] is True
    assert body["activated_at"] is not None

    assert len(recording_email_client.calls) == 1
    call = recording_email_client.calls[0]
    assert call["to"] == "target@u.com"
    assert call["full_name"] == "Tee"
    assert call["login_url"].endswith("/login")


def test_superadmin_can_also_activate(
    client, auth_headers, make_user, recording_email_client
):
    headers, _ = auth_headers(role="superadmin")
    target, _ = make_user(is_active=False)
    response = client.post(f"/auth/users/{target.id}/activate", headers=headers)
    assert response.status_code == 200
    assert len(recording_email_client.calls) == 1


def test_non_admin_cannot_activate(client, auth_headers, make_user):
    headers, _ = auth_headers(role="evaluator")
    target, _ = make_user(is_active=False)
    response = client.post(f"/auth/users/{target.id}/activate", headers=headers)
    assert response.status_code == 403


def test_viewer_cannot_activate(client, auth_headers, make_user):
    headers, _ = auth_headers(role="viewer")
    target, _ = make_user(is_active=False)
    response = client.post(f"/auth/users/{target.id}/activate", headers=headers)
    assert response.status_code == 403


def test_activate_unknown_user_returns_404(client, auth_headers):
    headers, _ = auth_headers(role="admin")
    response = client.post(f"/auth/users/{uuid.uuid4()}/activate", headers=headers)
    assert response.status_code == 404


def test_activate_already_active_is_idempotent_and_sends_no_email(
    client, auth_headers, make_user, recording_email_client
):
    headers, _ = auth_headers(role="admin")
    target, _ = make_user(is_active=True)
    response = client.post(f"/auth/users/{target.id}/activate", headers=headers)
    assert response.status_code == 200
    assert recording_email_client.calls == []


def test_activate_succeeds_even_if_email_fails(
    client, auth_headers, make_user, recording_email_client
):
    recording_email_client.fail_with = EmailSendError("simulated outage")
    headers, _ = auth_headers(role="admin")
    target, _ = make_user(is_active=False)
    response = client.post(f"/auth/users/{target.id}/activate", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is True
    assert len(recording_email_client.calls) == 1
