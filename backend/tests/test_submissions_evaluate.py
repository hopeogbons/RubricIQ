import io
import uuid

import pytest

from app.models import Learner, Rubric, SubmissionArtifact
from app.services.n8n_service import N8nTriggerError


@pytest.fixture()
def evaluable_submission(db_session, make_submission):
    """A draft submission with one GitHub-link artifact attached."""

    def _make(*, created_by=None, artifact_kind="link"):
        rub = Rubric(
            unique_name=f"r-{uuid.uuid4().hex[:8]}",
            display_name="R",
            created_by=created_by,
        )
        db_session.add(rub)
        db_session.flush()
        learner = Learner(
            rubric_id=rub.id,
            full_name="Jane Doe",
            email="jane@example.com",
            cohort="cohort-7",
        )
        db_session.add(learner)
        db_session.flush()
        sub = make_submission(rub, learner=learner, created_by=created_by)
        if artifact_kind == "link":
            db_session.add(
                SubmissionArtifact(
                    submission_id=sub.id,
                    type="github",
                    external_url="https://github.com/jane/proj",
                )
            )
        db_session.flush()
        return rub, learner, sub

    return _make


def _upload_screenshot(client, headers, sub_id, name="shot.png"):
    r = client.post(
        f"/submissions/{sub_id}/artifacts",
        headers=headers,
        data={"type": "screenshot"},
        files=[("files", (name, io.BytesIO(b"PNG"), "image/png"))],
    )
    assert r.status_code == 201
    return r.json()[0]


def test_admin_evaluate_flips_to_processing_and_sends_n8n_payload(
    client, auth_headers, evaluable_submission, recording_n8n_client
):
    headers, admin = auth_headers(role="admin")
    rub, learner, sub = evaluable_submission(created_by=admin.id)
    _upload_screenshot(client, headers, sub.id)

    response = client.post(f"/submissions/{sub.id}/evaluate", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "processing"
    assert body["triggered_at"] is not None

    assert len(recording_n8n_client.payloads) == 1
    payload = recording_n8n_client.payloads[0]
    # Flat top-level shape matches the n8n contract.
    assert payload["learner_id"] == str(learner.id)
    assert payload["assessment_id"] == rub.unique_name
    assert payload["cohort"] == "cohort-7"
    assert "callback_url" not in payload
    assert "callback_token" not in payload
    assert "submission_id" not in payload
    assert "learner" not in payload

    types = {a["type"] for a in payload["artifacts"]}
    assert types == {"github", "screenshot"}
    screenshot = next(a for a in payload["artifacts"] if a["type"] == "screenshot")
    assert "/artifacts/" in screenshot["url"]
    assert "filename" not in screenshot  # contract only exposes type + url
    github = next(a for a in payload["artifacts"] if a["type"] == "github")
    assert github["url"] == "https://github.com/jane/proj"


def test_evaluate_sends_text_artifact_value_not_url(
    client, auth_headers, evaluable_submission, db_session, recording_n8n_client
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = evaluable_submission(created_by=admin.id)
    db_session.add(
        SubmissionArtifact(
            submission_id=sub.id, type="text", text_value="hello world"
        )
    )
    db_session.flush()

    r = client.post(f"/submissions/{sub.id}/evaluate", headers=headers)
    assert r.status_code == 200
    payload = recording_n8n_client.payloads[0]
    text_artifact = next(a for a in payload["artifacts"] if a["type"] == "text")
    assert text_artifact == {"type": "text", "value": "hello world"}


def test_evaluator_can_evaluate_own_submission(
    client, auth_headers, evaluable_submission
):
    headers, evaluator = auth_headers(role="evaluator")
    _, _, sub = evaluable_submission(created_by=evaluator.id)
    r = client.post(f"/submissions/{sub.id}/evaluate", headers=headers)
    assert r.status_code == 200


def test_viewer_cannot_evaluate(client, auth_headers, evaluable_submission):
    headers, viewer = auth_headers(role="viewer")
    _, _, sub = evaluable_submission(created_by=viewer.id)
    r = client.post(f"/submissions/{sub.id}/evaluate", headers=headers)
    assert r.status_code == 403


def test_evaluate_out_of_scope_returns_404(
    client, auth_headers, evaluable_submission, make_user
):
    other_admin, _ = make_user(role="admin")
    _, _, sub = evaluable_submission(created_by=other_admin.id)
    eval_h, _ = auth_headers(role="evaluator")
    r = client.post(f"/submissions/{sub.id}/evaluate", headers=eval_h)
    assert r.status_code == 404


def test_evaluate_processing_returns_409(
    client, auth_headers, evaluable_submission, db_session
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = evaluable_submission(created_by=admin.id)
    sub.status = "processing"
    db_session.flush()
    r = client.post(f"/submissions/{sub.id}/evaluate", headers=headers)
    assert r.status_code == 409


def test_re_evaluate_complete_clears_prior_evaluation(
    client, auth_headers, evaluable_submission, db_session
):
    """Re-running on a complete submission resets it to processing and removes
    the prior evaluation row so the upcoming callback writes a fresh one."""
    from app.models import Evaluation, EvaluationScore

    headers, admin = auth_headers(role="admin")
    _, _, sub = evaluable_submission(created_by=admin.id)
    sub.status = "complete"
    ev = Evaluation(submission_id=sub.id, total_score=10, max_total=10)
    db_session.add(ev)
    db_session.flush()
    db_session.add(
        EvaluationScore(evaluation_id=ev.id, criterion="x", score=1, max_score=1)
    )
    db_session.flush()
    old_ev_id = ev.id

    r = client.post(f"/submissions/{sub.id}/evaluate", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "processing"
    assert body["evaluation"] is None
    db_session.expire_all()
    from sqlalchemy import select

    assert (
        db_session.scalar(select(Evaluation).where(Evaluation.id == old_ev_id)) is None
    )


def test_evaluate_with_no_artifacts_returns_400(
    client, auth_headers, db_session, make_submission
):
    headers, admin = auth_headers(role="admin")
    rub = Rubric(
        unique_name=f"r-{uuid.uuid4().hex[:8]}", display_name="R", created_by=admin.id
    )
    db_session.add(rub)
    db_session.flush()
    learner = Learner(rubric_id=rub.id, full_name="L")
    db_session.add(learner)
    db_session.flush()
    sub = make_submission(rub, learner=learner, created_by=admin.id)
    r = client.post(f"/submissions/{sub.id}/evaluate", headers=headers)
    assert r.status_code == 400


def test_n8n_failure_returns_502_and_keeps_state(
    client, auth_headers, evaluable_submission, recording_n8n_client, db_session
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = evaluable_submission(created_by=admin.id)
    recording_n8n_client.fail_with = N8nTriggerError("simulated outage")
    r = client.post(f"/submissions/{sub.id}/evaluate", headers=headers)
    assert r.status_code == 502
    db_session.refresh(sub)
    assert sub.status == "draft"
    assert sub.triggered_at is None


def test_unauthenticated_cannot_evaluate(client, evaluable_submission, make_user):
    other_admin, _ = make_user(role="admin")
    _, _, sub = evaluable_submission(created_by=other_admin.id)
    r = client.post(f"/submissions/{sub.id}/evaluate")
    assert r.status_code == 401
