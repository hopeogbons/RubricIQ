import io
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models import Learner, Rubric, SubmissionArtifact
from app.services.artifact_token import issue_artifact_token


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


def _upload(client, headers, sub_id, name="shot.png", data=b"PNGCONTENT"):
    r = client.post(
        f"/submissions/{sub_id}/artifacts",
        headers=headers,
        data={"type": "screenshot"},
        files=[("files", (name, io.BytesIO(data), "image/png"))],
    )
    assert r.status_code == 201
    return r.json()[0]


def test_valid_token_streams_file_with_correct_mime(
    client, auth_headers, draft_submission
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    artifact = _upload(client, headers, sub.id)

    token = issue_artifact_token(sub.id, artifact["filename"])
    r = client.get(f"/artifacts/{token}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")
    assert r.content == b"PNGCONTENT"


def test_expired_token_returns_401(client, auth_headers, draft_submission):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    artifact = _upload(client, headers, sub.id)
    past = datetime.now(tz=UTC) - timedelta(hours=3)
    token = issue_artifact_token(sub.id, artifact["filename"], ttl_seconds=60, now=past)
    r = client.get(f"/artifacts/{token}")
    assert r.status_code == 401


def test_tampered_token_returns_401(client, auth_headers, draft_submission):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    artifact = _upload(client, headers, sub.id)
    token = issue_artifact_token(sub.id, artifact["filename"])
    head, payload, _sig = token.split(".")
    r = client.get(f"/artifacts/{head}.{payload}.AAAA")
    assert r.status_code == 401


def test_token_for_unknown_filename_returns_404(
    client, auth_headers, draft_submission
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    _upload(client, headers, sub.id, name="real.png")
    token = issue_artifact_token(sub.id, "phantom.png")
    r = client.get(f"/artifacts/{token}")
    assert r.status_code == 404


def test_token_when_db_row_present_but_file_missing_returns_404(
    client, auth_headers, draft_submission
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    artifact = _upload(client, headers, sub.id)
    # Remove the file from disk but leave the DB row
    file_path = os.path.join(os.environ["ARTIFACT_DIR"], str(sub.id), artifact["filename"])
    os.unlink(file_path)
    token = issue_artifact_token(sub.id, artifact["filename"])
    r = client.get(f"/artifacts/{token}")
    assert r.status_code == 404


def test_token_for_link_artifact_does_not_resolve(
    client, draft_submission, db_session, auth_headers
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    link = SubmissionArtifact(
        submission_id=sub.id, type="video_link", external_url="https://loom.com/x"
    )
    db_session.add(link)
    db_session.flush()
    # No real filename for links; even if attacker fabricates one, the type filter blocks
    token = issue_artifact_token(sub.id, "made-up.png")
    r = client.get(f"/artifacts/{token}")
    assert r.status_code == 404
