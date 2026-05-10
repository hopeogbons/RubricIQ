import io
import os
import uuid

import pytest

from app.models import Learner, Rubric, SubmissionArtifact


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


def _upload_one(client, headers, sub_id, name="shot.png"):
    r = client.post(
        f"/submissions/{sub_id}/artifacts",
        headers=headers,
        data={"type": "screenshot"},
        files=[("files", (name, io.BytesIO(b"PNG"), "image/png"))],
    )
    assert r.status_code == 201
    return r.json()[0]


def test_delete_file_artifact_removes_db_row_and_file(
    client, auth_headers, draft_submission
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    artifact = _upload_one(client, headers, sub.id)
    file_path = os.path.join(os.environ["ARTIFACT_DIR"], str(sub.id), artifact["filename"])
    assert os.path.isfile(file_path)

    r = client.delete(
        f"/submissions/{sub.id}/artifacts/{artifact['id']}", headers=headers
    )
    assert r.status_code == 204
    assert not os.path.isfile(file_path)


def test_delete_link_artifact(client, auth_headers, draft_submission, db_session):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    link = SubmissionArtifact(
        submission_id=sub.id, type="github_link", external_url="https://github.com/x/y"
    )
    db_session.add(link)
    db_session.flush()
    r = client.delete(
        f"/submissions/{sub.id}/artifacts/{link.id}", headers=headers
    )
    assert r.status_code == 204


def test_delete_unknown_artifact_returns_404(
    client, auth_headers, draft_submission
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    r = client.delete(
        f"/submissions/{sub.id}/artifacts/{uuid.uuid4()}", headers=headers
    )
    assert r.status_code == 404


def test_delete_artifact_belonging_to_other_submission_returns_404(
    client, auth_headers, draft_submission
):
    headers, admin = auth_headers(role="admin")
    _, _, sub_a = draft_submission(created_by=admin.id)
    _, _, sub_b = draft_submission(created_by=admin.id)
    artifact = _upload_one(client, headers, sub_a.id, name="a.png")
    r = client.delete(
        f"/submissions/{sub_b.id}/artifacts/{artifact['id']}", headers=headers
    )
    assert r.status_code == 404


def test_delete_blocked_once_submission_processes(
    client, auth_headers, draft_submission, db_session
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    artifact = _upload_one(client, headers, sub.id)
    sub.status = "processing"
    db_session.flush()
    r = client.delete(
        f"/submissions/{sub.id}/artifacts/{artifact['id']}", headers=headers
    )
    assert r.status_code == 409


def test_viewer_cannot_delete(client, auth_headers, draft_submission, db_session):
    headers, viewer = auth_headers(role="viewer")
    _, _, sub = draft_submission(created_by=viewer.id)
    link = SubmissionArtifact(
        submission_id=sub.id, type="video_link", external_url="https://loom.com/x"
    )
    db_session.add(link)
    db_session.flush()
    r = client.delete(
        f"/submissions/{sub.id}/artifacts/{link.id}", headers=headers
    )
    assert r.status_code == 403
