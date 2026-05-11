import io
import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.config import settings
from app.models import Evaluation, EvaluationScore, Learner, Rubric

CALLBACK_PATH = "/webhooks/n8n-callback"


def _auth_headers() -> dict[str, str]:
    return {"X-API-Key": settings.callback_secret}


@pytest.fixture()
def processing_submission(db_session, make_submission, client, auth_headers):
    """A submission already in 'processing' state with an on-disk screenshot artifact."""
    def _make():
        headers, admin = auth_headers(role="admin")
        rub = Rubric(
            unique_name=f"r-{uuid.uuid4().hex[:8]}",
            display_name="R",
            created_by=admin.id,
        )
        db_session.add(rub)
        db_session.flush()
        learner = Learner(rubric_id=rub.id, full_name="L")
        db_session.add(learner)
        db_session.flush()
        sub = make_submission(rub, learner=learner, created_by=admin.id)

        client.post(
            f"/submissions/{sub.id}/artifacts",
            headers=headers,
            data={"type": "screenshot"},
            files=[("files", ("a.png", io.BytesIO(b"PNG"), "image/png"))],
        )
        sub.status = "processing"
        sub.triggered_at = datetime.now(tz=UTC)
        db_session.flush()
        return sub

    return _make


def test_complete_callback_writes_evaluation_and_scores(
    client, processing_submission, db_session
):
    sub = processing_submission()
    artifact_dir = os.path.join(os.environ["ARTIFACT_DIR"], str(sub.id))
    assert os.path.isdir(artifact_dir)

    body = {
        "learner_id": str(sub.learner_id),
        "status": "complete",
        "evaluation": {
            "total_score": 18,
            "max_total": 25,
            "scores": [
                {
                    "criterion": "Code quality",
                    "score": 4,
                    "max": 5,
                    "explanation": "Clean.",
                },
                {
                    "criterion": "Tests",
                    "score": 3,
                    "max": 5,
                    "explanation": "Some gaps.",
                },
            ],
        },
    }
    r = client.post(CALLBACK_PATH, json=body, headers=_auth_headers())
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "complete"
    assert out["evaluation"]["total_score"] == 18.0
    assert {s["criterion"] for s in out["evaluation"]["scores"]} == {
        "Code quality",
        "Tests",
    }

    db_session.expire_all()
    ev = db_session.scalar(select(Evaluation).where(Evaluation.submission_id == sub.id))
    assert ev is not None
    assert ev.raw_response is not None  # full payload captured

    # Artifacts dir cleaned up
    assert not os.path.isdir(artifact_dir)


def test_failed_callback_sets_error_and_no_evaluation(
    client, processing_submission, db_session
):
    sub = processing_submission()
    body = {
        "learner_id": str(sub.learner_id),
        "status": "failed",
        "error_message": "n8n workflow blew up",
    }
    r = client.post(CALLBACK_PATH, json=body, headers=_auth_headers())
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "failed"
    assert out["error_message"] == "n8n workflow blew up"
    assert out["evaluation"] is None

    db_session.expire_all()
    ev = db_session.scalar(select(Evaluation).where(Evaluation.submission_id == sub.id))
    assert ev is None
    artifact_dir = os.path.join(os.environ["ARTIFACT_DIR"], str(sub.id))
    assert not os.path.isdir(artifact_dir)


def test_complete_without_evaluation_payload_returns_400(
    client, processing_submission
):
    sub = processing_submission()
    r = client.post(
        CALLBACK_PATH,
        json={"learner_id": str(sub.learner_id), "status": "complete"},
        headers=_auth_headers(),
    )
    assert r.status_code == 400


def test_missing_api_key_returns_401(client, processing_submission):
    sub = processing_submission()
    r = client.post(
        CALLBACK_PATH,
        json={
            "learner_id": str(sub.learner_id),
            "status": "failed",
            "error_message": "x",
        },
    )
    assert r.status_code == 401


def test_wrong_api_key_returns_401(client, processing_submission):
    sub = processing_submission()
    r = client.post(
        CALLBACK_PATH,
        json={
            "learner_id": str(sub.learner_id),
            "status": "failed",
            "error_message": "x",
        },
        headers={"X-API-Key": "not-the-right-secret"},
    )
    assert r.status_code == 401


def test_callback_for_unknown_learner_returns_404(client):
    r = client.post(
        CALLBACK_PATH,
        json={
            "learner_id": str(uuid.uuid4()),
            "status": "failed",
            "error_message": "x",
        },
        headers=_auth_headers(),
    )
    assert r.status_code == 404


def test_callback_idempotent_on_already_complete_submission(
    client, processing_submission, db_session
):
    sub = processing_submission()
    body = {
        "learner_id": str(sub.learner_id),
        "status": "complete",
        "evaluation": {
            "total_score": 18,
            "max_total": 25,
            "scores": [{"criterion": "x", "score": 1, "max": 1}],
        },
    }
    assert (
        client.post(CALLBACK_PATH, json=body, headers=_auth_headers()).status_code == 200
    )

    # Second delivery with totally different scores must be a no-op
    second = dict(body)
    second["evaluation"] = {
        "total_score": 0,
        "max_total": 25,
        "scores": [{"criterion": "y", "score": 0, "max": 5}],
    }
    r = client.post(CALLBACK_PATH, json=second, headers=_auth_headers())
    assert r.status_code == 200
    out = r.json()
    assert out["evaluation"]["total_score"] == 18.0
    db_session.expire_all()
    score_count = db_session.scalar(
        select(EvaluationScore).where(EvaluationScore.criterion == "y")
    )
    assert score_count is None


def test_callback_idempotent_on_already_failed_submission(
    client, processing_submission, db_session
):
    sub = processing_submission()
    sub.status = "failed"
    sub.error_message = "first failure"
    db_session.flush()
    body = {
        "learner_id": str(sub.learner_id),
        "status": "complete",
        "evaluation": {
            "total_score": 99,
            "max_total": 100,
            "scores": [],
        },
    }
    r = client.post(CALLBACK_PATH, json=body, headers=_auth_headers())
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "failed"
    assert out["error_message"] == "first failure"
    assert out["evaluation"] is None
