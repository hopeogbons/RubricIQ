import uuid


def _payload(**overrides):
    return {
        "unique_name": f"rub-{uuid.uuid4().hex[:8]}",
        "display_name": "Test Rubric",
        "description": "desc",
        **overrides,
    }


def test_admin_creates_rubric(client, auth_headers):
    headers, admin = auth_headers(role="admin")
    response = client.post("/rubrics", headers=headers, json=_payload(unique_name="my-rubric"))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["unique_name"] == "my-rubric"
    assert body["display_name"] == "Test Rubric"
    assert body["created_by"] == str(admin.id)


def test_superadmin_creates_rubric(client, auth_headers):
    headers, _ = auth_headers(role="superadmin")
    response = client.post("/rubrics", headers=headers, json=_payload())
    assert response.status_code == 201


def test_evaluator_cannot_create_rubric(client, auth_headers):
    headers, _ = auth_headers(role="evaluator")
    response = client.post("/rubrics", headers=headers, json=_payload())
    assert response.status_code == 403


def test_viewer_cannot_create_rubric(client, auth_headers):
    headers, _ = auth_headers(role="viewer")
    response = client.post("/rubrics", headers=headers, json=_payload())
    assert response.status_code == 403


def test_unauthenticated_cannot_create_rubric(client):
    response = client.post("/rubrics", json=_payload())
    assert response.status_code == 401


def test_unique_name_must_be_slug(client, auth_headers):
    headers, _ = auth_headers(role="admin")
    response = client.post("/rubrics", headers=headers, json=_payload(unique_name="Has Spaces"))
    assert response.status_code == 422


def test_unique_name_uppercase_rejected(client, auth_headers):
    headers, _ = auth_headers(role="admin")
    response = client.post("/rubrics", headers=headers, json=_payload(unique_name="UPPER"))
    assert response.status_code == 422


def test_duplicate_unique_name_returns_400(client, auth_headers):
    headers, _ = auth_headers(role="admin")
    p = _payload(unique_name="dup-name")
    assert client.post("/rubrics", headers=headers, json=p).status_code == 201
    response = client.post("/rubrics", headers=headers, json=p)
    assert response.status_code == 400


def test_admin_patches_mutable_fields(client, auth_headers):
    headers, _ = auth_headers(role="admin")
    created = client.post("/rubrics", headers=headers, json=_payload()).json()
    response = client.patch(
        f"/rubrics/{created['id']}",
        headers=headers,
        json={"display_name": "New Name", "description": "new desc"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["display_name"] == "New Name"
    assert body["description"] == "new desc"
    assert body["unique_name"] == created["unique_name"]


def test_patch_unique_name_silently_ignored(client, auth_headers):
    headers, _ = auth_headers(role="admin")
    payload = _payload(unique_name="orig-slug")
    created = client.post("/rubrics", headers=headers, json=payload).json()
    response = client.patch(
        f"/rubrics/{created['id']}",
        headers=headers,
        json={"unique_name": "tried-to-rename", "display_name": "Renamed"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["unique_name"] == "orig-slug"
    assert body["display_name"] == "Renamed"


def test_evaluator_cannot_patch_rubric(client, auth_headers):
    admin_h, _ = auth_headers(role="admin")
    created = client.post("/rubrics", headers=admin_h, json=_payload()).json()
    eval_h, _ = auth_headers(role="evaluator")
    response = client.patch(
        f"/rubrics/{created['id']}", headers=eval_h, json={"display_name": "X"}
    )
    assert response.status_code == 403


def test_admin_deletes_rubric(client, auth_headers):
    headers, _ = auth_headers(role="admin")
    created = client.post("/rubrics", headers=headers, json=_payload()).json()
    response = client.delete(f"/rubrics/{created['id']}", headers=headers)
    assert response.status_code == 204
    assert client.get(f"/rubrics/{created['id']}", headers=headers).status_code == 404


def test_evaluator_cannot_delete_rubric(client, auth_headers):
    admin_h, _ = auth_headers(role="admin")
    created = client.post("/rubrics", headers=admin_h, json=_payload()).json()
    eval_h, _ = auth_headers(role="evaluator")
    response = client.delete(f"/rubrics/{created['id']}", headers=eval_h)
    assert response.status_code == 403


def test_delete_unknown_rubric_returns_404(client, auth_headers):
    headers, _ = auth_headers(role="admin")
    response = client.delete(f"/rubrics/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404
