import uuid
from datetime import UTC, datetime

import pytest

from app.models import Evaluation, EvaluationScore, Learner, Rubric


@pytest.fixture()
def rubric_with_submission(db_session, make_submission):
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
        sub = make_submission(rub, learner=learner, created_by=created_by)
        return rub, learner, sub

    return _make


def test_admin_gets_submission_detail_with_no_evaluation(
    client, auth_headers, rubric_with_submission
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = rubric_with_submission(created_by=admin.id)
    response = client.get(f"/submissions/{sub.id}", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(sub.id)
    assert body["status"] == "draft"
    assert body["evaluation"] is None
    assert body["artifacts"] == []


def test_submission_detail_with_evaluation_includes_scores(
    client, auth_headers, rubric_with_submission, db_session
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = rubric_with_submission(created_by=admin.id)
    sub.status = "complete"
    sub.completed_at = datetime.now(tz=UTC)
    db_session.flush()
    ev = Evaluation(submission_id=sub.id, total_score=18, max_total=25)
    db_session.add(ev)
    db_session.flush()
    db_session.add(
        EvaluationScore(
            evaluation_id=ev.id,
            criterion="Code quality",
            score=4,
            max_score=5,
            explanation="Clean.",
        )
    )
    db_session.flush()

    response = client.get(f"/submissions/{sub.id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert body["evaluation"]["total_score"] == 18.0
    assert body["evaluation"]["max_total"] == 25.0
    assert len(body["evaluation"]["scores"]) == 1
    assert body["evaluation"]["scores"][0]["criterion"] == "Code quality"


def test_submission_status_endpoint_is_lightweight(
    client, auth_headers, rubric_with_submission
):
    headers, admin = auth_headers(role="admin")
    _, _, sub = rubric_with_submission(created_by=admin.id)
    response = client.get(f"/submissions/{sub.id}/status", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "id",
        "status",
        "triggered_at",
        "completed_at",
        "error_message",
        "total_score",
        "evaluated_at",
    }


def test_evaluator_cannot_read_out_of_scope_submission(
    client, auth_headers, rubric_with_submission, make_user
):
    other_admin, _ = make_user(role="admin")
    _, _, sub = rubric_with_submission(created_by=other_admin.id)
    headers, _ = auth_headers(role="evaluator")
    response = client.get(f"/submissions/{sub.id}", headers=headers)
    assert response.status_code == 404


def test_unknown_submission_returns_404(client, auth_headers):
    headers, _ = auth_headers(role="admin")
    response = client.get(f"/submissions/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


def test_unauthenticated_cannot_read(client, rubric_with_submission, make_user):
    other_admin, _ = make_user(role="admin")
    _, _, sub = rubric_with_submission(created_by=other_admin.id)
    response = client.get(f"/submissions/{sub.id}")
    assert response.status_code == 401
