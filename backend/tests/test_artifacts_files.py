import io
import os
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


def _file(name: str, data: bytes, content_type: str = "application/octet-stream"):
    return ("files", (name, io.BytesIO(data), content_type))


def test_admin_uploads_screenshot(client, auth_headers, draft_submission):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    response = client.post(
        f"/submissions/{sub.id}/artifacts",
        headers=headers,
        data={"type": "screenshot"},
        files=[_file("dashboard.png", b"PNGDATA", "image/png")],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]["type"] == "screenshot"
    assert body[0]["filename"] == "dashboard.png"
    assert body[0]["size_bytes"] == len(b"PNGDATA")


def test_video_file_upload_rejected(client, auth_headers, draft_submission):
    """Direct video file uploads are no longer accepted; videos come in as Loom
    or Google Drive links."""
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    r = client.post(
        f"/submissions/{sub.id}/artifacts",
        headers=headers,
        data={"type": "video_file"},
        files=[_file("a.mp4", b"VID", "video/mp4")],
    )
    assert r.status_code == 422


def test_disallowed_extension_rejected(client, auth_headers, draft_submission):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    r = client.post(
        f"/submissions/{sub.id}/artifacts",
        headers=headers,
        data={"type": "screenshot"},
        files=[_file("notes.pdf", b"PDF")],
    )
    assert r.status_code == 422


def test_unknown_type_rejected(client, auth_headers, draft_submission):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    r = client.post(
        f"/submissions/{sub.id}/artifacts",
        headers=headers,
        data={"type": "invalid_kind"},
        files=[_file("x.png", b"x")],
    )
    assert r.status_code == 422


def test_per_file_size_limit_rejected_and_cleaned(
    client, auth_headers, draft_submission
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    big = b"x" * (10 * 1024 + 1)  # 1 byte over 10 KB test limit
    r = client.post(
        f"/submissions/{sub.id}/artifacts",
        headers=headers,
        data={"type": "screenshot"},
        files=[_file("big.png", big)],
    )
    assert r.status_code == 413
    # File must not be on disk
    artifact_dir = os.environ["ARTIFACT_DIR"]
    sub_dir = os.path.join(artifact_dir, str(sub.id))
    if os.path.isdir(sub_dir):
        assert "big.png" not in os.listdir(sub_dir)


def test_per_submission_size_limit_rejects_overflow(
    client, auth_headers, draft_submission
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    # MAX_SUBMISSION_BYTES is 50KB in tests; MAX_FILE_BYTES is 10KB.
    payload = b"y" * (10 * 1024)
    # Five 10 KB uploads = 50 KB total (allowed)
    for i in range(5):
        r = client.post(
            f"/submissions/{sub.id}/artifacts",
            headers=headers,
            data={"type": "screenshot"},
            files=[_file(f"shot{i}.png", payload)],
        )
        assert r.status_code == 201, r.text
    # 6th would exceed
    r = client.post(
        f"/submissions/{sub.id}/artifacts",
        headers=headers,
        data={"type": "screenshot"},
        files=[_file("shot5.png", payload)],
    )
    assert r.status_code == 413
    artifact_dir = os.environ["ARTIFACT_DIR"]
    sub_dir = os.path.join(artifact_dir, str(sub.id))
    assert "shot5.png" not in os.listdir(sub_dir)
    # Earlier files still present
    assert "shot0.png" in os.listdir(sub_dir)


def test_duplicate_filename_rejected(client, auth_headers, draft_submission):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    payload = {"type": "screenshot"}
    files = [_file("same.png", b"a")]
    assert client.post(
        f"/submissions/{sub.id}/artifacts", headers=headers, data=payload, files=files
    ).status_code == 201
    r = client.post(
        f"/submissions/{sub.id}/artifacts",
        headers=headers,
        data=payload,
        files=[_file("same.png", b"b")],
    )
    assert r.status_code == 400


def test_upload_to_processing_returns_409(
    client, auth_headers, draft_submission, db_session
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    sub.status = "processing"
    db_session.flush()
    r = client.post(
        f"/submissions/{sub.id}/artifacts",
        headers=headers,
        data={"type": "screenshot"},
        files=[_file("x.png", b"x")],
    )
    assert r.status_code == 409


def test_upload_to_complete_submission_allowed(
    client, auth_headers, draft_submission, db_session
):
    """Editing artifacts on a complete submission is allowed so the evaluator
    can iterate before re-running n8n."""
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    sub.status = "complete"
    db_session.flush()
    r = client.post(
        f"/submissions/{sub.id}/artifacts",
        headers=headers,
        data={"type": "screenshot"},
        files=[_file("x.png", b"x")],
    )
    assert r.status_code == 201


def test_viewer_cannot_upload(client, auth_headers, draft_submission):
    headers, viewer = auth_headers(role="viewer")
    _, _, sub = draft_submission(created_by=viewer.id)
    r = client.post(
        f"/submissions/{sub.id}/artifacts",
        headers=headers,
        data={"type": "screenshot"},
        files=[_file("x.png", b"x")],
    )
    assert r.status_code == 403


def test_unauthenticated_cannot_upload(client, draft_submission, make_user):
    other_admin, _ = make_user(role="admin")
    _, _, sub = draft_submission(created_by=other_admin.id)
    r = client.post(
        f"/submissions/{sub.id}/artifacts",
        data={"type": "screenshot"},
        files=[_file("x.png", b"x")],
    )
    assert r.status_code == 401


def test_filename_traversal_stripped(client, auth_headers, draft_submission):
    headers, admin = auth_headers(role="admin")
    _, _, sub = draft_submission(created_by=admin.id)
    r = client.post(
        f"/submissions/{sub.id}/artifacts",
        headers=headers,
        data={"type": "screenshot"},
        files=[_file("../../etc/passwd.png", b"x")],
    )
    assert r.status_code == 201
    assert r.json()[0]["filename"] == "passwd.png"
