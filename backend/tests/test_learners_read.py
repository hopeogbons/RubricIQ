import uuid
from datetime import UTC, datetime

import pytest

from app.models import Evaluation, Learner, Rubric, Submission


@pytest.fixture()
def make_rubric(db_session):
    counter = {"n": 0}

    def _make(*, created_by=None):
        counter["n"] += 1
        rub = Rubric(
            unique_name=f"rub-{counter['n']}-{uuid.uuid4().hex[:6]}",
            display_name="R",
            created_by=created_by,
        )
        db_session.add(rub)
        db_session.flush()
        return rub

    return _make


def test_admin_lists_learners(client, auth_headers, make_rubric, db_session):
    headers, admin = auth_headers(role="admin")
    rub = make_rubric(created_by=admin.id)
    db_session.add_all([
        Learner(rubric_id=rub.id, full_name="A"),
        Learner(rubric_id=rub.id, full_name="B"),
    ])
    db_session.flush()

    response = client.get(f"/rubrics/{rub.id}/learners", headers=headers)
    assert response.status_code == 200
    names = {row["full_name"] for row in response.json()}
    assert names == {"A", "B"}


def test_list_learners_in_unowned_rubric_returns_404(
    client, auth_headers, make_user, make_rubric, db_session
):
    other_admin, _ = make_user(role="admin")
    rub = make_rubric(created_by=other_admin.id)
    db_session.add(Learner(rubric_id=rub.id, full_name="A"))
    db_session.flush()

    eval_h, _ = auth_headers(role="evaluator")
    response = client.get(f"/rubrics/{rub.id}/learners", headers=eval_h)
    assert response.status_code == 404


def test_learner_detail_includes_single_submission_and_scores(
    client, auth_headers, make_rubric, db_session
):
    headers, admin = auth_headers(role="admin")
    rub = make_rubric(created_by=admin.id)
    learner = Learner(rubric_id=rub.id, full_name="Jane", email="jane@example.com")
    db_session.add(learner)
    db_session.flush()

    sub = Submission(
        learner_id=learner.id,
        rubric_id=rub.id,
        status="complete",
        completed_at=datetime.now(tz=UTC),
    )
    db_session.add(sub)
    db_session.flush()
    db_session.add(Evaluation(submission_id=sub.id, total_score=18, max_total=25))
    db_session.flush()

    response = client.get(f"/learners/{learner.id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Jane"
    assert len(body["submissions"]) == 1  # one record per learner
    only = body["submissions"][0]
    assert only["status"] == "complete"
    assert only["total_score"] == 18.0
    assert only["max_total"] == 25.0
    assert only["evaluated_at"] is not None


def test_learner_detail_out_of_scope_returns_404(
    client, auth_headers, make_user, make_rubric, db_session
):
    other_admin, _ = make_user(role="admin")
    rub = make_rubric(created_by=other_admin.id)
    learner = Learner(rubric_id=rub.id, full_name="Hidden")
    db_session.add(learner)
    db_session.flush()

    eval_h, _ = auth_headers(role="evaluator")
    response = client.get(f"/learners/{learner.id}", headers=eval_h)
    assert response.status_code == 404


def test_learner_detail_unknown_id_returns_404(client, auth_headers):
    headers, _ = auth_headers(role="admin")
    response = client.get(f"/learners/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


def test_unauthenticated_cannot_get_learner(client, make_rubric, make_user, db_session):
    other_admin, _ = make_user(role="admin")
    rub = make_rubric(created_by=other_admin.id)
    learner = Learner(rubric_id=rub.id, full_name="X")
    db_session.add(learner)
    db_session.flush()
    response = client.get(f"/learners/{learner.id}")
    assert response.status_code == 401
