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


def test_admin_adds_loom_gdrive_and_github_links(
    client, auth_headers, draft_submission
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    r = client.post(
        f"/submissions/{sub.id}/artifacts/links",
        headers=headers,
        json={
            "links": [
                {"type": "loom", "url": "https://loom.com/share/abc"},
                {"type": "gdrive_video", "url": "https://drive.google.com/file/d/x"},
                {"type": "github", "url": "https://github.com/jane/proj"},
            ]
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert {a["type"] for a in body} == {"loom", "gdrive_video", "github"}
    assert all(a["external_url"] for a in body)
    assert all(a["filename"] is None for a in body)


def test_invalid_url_rejected(client, auth_headers, draft_submission):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    r = client.post(
        f"/submissions/{sub.id}/artifacts/links",
        headers=headers,
        json={"links": [{"type": "github", "url": "not-a-url"}]},
    )
    assert r.status_code == 422


def test_file_type_rejected_in_links_endpoint(
    client, auth_headers, draft_submission
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    r = client.post(
        f"/submissions/{sub.id}/artifacts/links",
        headers=headers,
        json={"links": [{"type": "screenshot", "url": "https://x.com/y"}]},
    )
    assert r.status_code == 422


def test_links_post_to_non_draft_returns_409(
    client, auth_headers, draft_submission, db_session
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    sub.status = "processing"
    db_session.flush()
    r = client.post(
        f"/submissions/{sub.id}/artifacts/links",
        headers=headers,
        json={"links": [{"type": "loom", "url": "https://loom.com/x"}]},
    )
    assert r.status_code == 409


def test_viewer_cannot_post_links(client, auth_headers, draft_submission):
    headers, viewer = auth_headers(role="viewer")
    _, _, sub = draft_submission(created_by=viewer.id)
    r = client.post(
        f"/submissions/{sub.id}/artifacts/links",
        headers=headers,
        json={"links": [{"type": "loom", "url": "https://loom.com/x"}]},
    )
    assert r.status_code == 403
