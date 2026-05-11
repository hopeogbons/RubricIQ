import uuid

import pytest

from app.models import Learner, Rubric, Submission


@pytest.fixture()
def make_rubric(db_session):
    counter = {"n": 0}

    def _make(*, created_by=None, unique_name=None, display_name="R"):
        counter["n"] += 1
        rub = Rubric(
            unique_name=unique_name or f"rub-{counter['n']}-{uuid.uuid4().hex[:6]}",
            display_name=display_name,
            created_by=created_by,
        )
        db_session.add(rub)
        db_session.flush()
        return rub

    return _make


def test_admin_sees_all_rubrics(client, auth_headers, make_user, make_rubric):
    other_admin, _ = make_user(role="admin")
    make_rubric(created_by=other_admin.id)
    make_rubric(created_by=other_admin.id)
    headers, _ = auth_headers(role="admin")
    response = client.get("/rubrics", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_evaluator_sees_only_own_and_submission_rubrics(
    client, auth_headers, make_user, make_rubric, db_session
):
    headers, evaluator = auth_headers(role="evaluator")
    other_admin, _ = make_user(role="admin")

    own = make_rubric(created_by=evaluator.id, display_name="Own")
    via_submission_owner_rub = make_rubric(created_by=other_admin.id, display_name="Via Submission")
    invisible = make_rubric(created_by=other_admin.id, display_name="Invisible")

    learner = Learner(rubric_id=via_submission_owner_rub.id, full_name="L")
    db_session.add(learner)
    db_session.flush()
    sub = Submission(
        learner_id=learner.id,
        rubric_id=via_submission_owner_rub.id,
        created_by=evaluator.id,
        status="draft",
    )
    db_session.add(sub)
    db_session.flush()

    response = client.get("/rubrics", headers=headers)
    assert response.status_code == 200
    visible_ids = {r["id"] for r in response.json()}
    assert str(own.id) in visible_ids
    assert str(via_submission_owner_rub.id) in visible_ids
    assert str(invisible.id) not in visible_ids


def test_viewer_sees_only_own_rubrics(client, auth_headers, make_user, make_rubric):
    headers, viewer = auth_headers(role="viewer")
    other_admin, _ = make_user(role="admin")
    own = make_rubric(created_by=viewer.id)
    invisible = make_rubric(created_by=other_admin.id)

    response = client.get("/rubrics", headers=headers)
    assert response.status_code == 200
    visible = {r["id"] for r in response.json()}
    assert str(own.id) in visible
    assert str(invisible.id) not in visible


def test_unauthenticated_cannot_list(client):
    response = client.get("/rubrics")
    assert response.status_code == 401


def test_detail_out_of_scope_returns_404(client, auth_headers, make_user, make_rubric):
    other_admin, _ = make_user(role="admin")
    rub = make_rubric(created_by=other_admin.id)
    eval_headers, _ = auth_headers(role="evaluator")
    response = client.get(f"/rubrics/{rub.id}", headers=eval_headers)
    assert response.status_code == 404


def test_detail_includes_stats(
    client, auth_headers, make_rubric, db_session
):
    """One submission per learner; two learners give two submissions for the stats."""
    headers, admin = auth_headers(role="admin")
    rub = make_rubric(created_by=admin.id)
    learner_a = Learner(rubric_id=rub.id, full_name="A")
    learner_b = Learner(rubric_id=rub.id, full_name="B")
    db_session.add_all([learner_a, learner_b])
    db_session.flush()
    db_session.add_all([
        Submission(learner_id=learner_a.id, rubric_id=rub.id, status="complete"),
        Submission(learner_id=learner_b.id, rubric_id=rub.id, status="draft"),
    ])
    db_session.flush()

    response = client.get(f"/rubrics/{rub.id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["learner_count"] == 2
    assert body["submission_count"] == 2
    assert body["completion_rate"] == 0.5


def test_detail_no_submissions_completion_rate_zero(
    client, auth_headers, make_rubric
):
    headers, admin = auth_headers(role="admin")
    rub = make_rubric(created_by=admin.id)
    response = client.get(f"/rubrics/{rub.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["completion_rate"] == 0.0


def test_detail_unknown_rubric_returns_404(client, auth_headers):
    headers, _ = auth_headers(role="admin")
    response = client.get(f"/rubrics/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404
