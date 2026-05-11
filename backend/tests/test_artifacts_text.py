import uuid

import pytest

from app.models import Learner, Rubric


@pytest.fixture()
def draft_submission(db_session, make_submission):
    def _make(*, created_by=None):
        rub = Rubric(
            unique_name=f"r-{uuid.uuid4().hex[:8]}",
            display_name="R",
            created_by=created_by,
        )
        db_session.add(rub)
        db_session.flush()
        learner = Learner(rubric_id=rub.id, full_name="L")
        db_session.add(learner)
        db_session.flush()
        return rub, learner, make_submission(rub, learner=learner, created_by=created_by)

    return _make


def test_admin_adds_text_artifact(client, auth_headers, draft_submission):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    r = client.post(
        f"/submissions/{sub.id}/artifacts/text",
        headers=headers,
        json={"value": "free-form notes about the work"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["type"] == "text"
    assert body["text_value"] == "free-form notes about the work"
    assert body["filename"] is None
    assert body["external_url"] is None


def test_empty_value_rejected(client, auth_headers, draft_submission):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    r = client.post(
        f"/submissions/{sub.id}/artifacts/text",
        headers=headers,
        json={"value": ""},
    )
    assert r.status_code == 422


def test_text_post_to_processing_returns_409(
    client, auth_headers, draft_submission, db_session
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    sub.status = "processing"
    db_session.flush()
    r = client.post(
        f"/submissions/{sub.id}/artifacts/text",
        headers=headers,
        json={"value": "x"},
    )
    assert r.status_code == 409


def test_viewer_cannot_post_text(client, auth_headers, draft_submission):
    headers, viewer = auth_headers(role="viewer")
    _, _, sub = draft_submission(created_by=viewer.id)
    r = client.post(
        f"/submissions/{sub.id}/artifacts/text",
        headers=headers,
        json={"value": "x"},
    )
    assert r.status_code == 403
