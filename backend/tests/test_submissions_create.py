import uuid

import pytest

from app.models import Learner, Rubric


@pytest.fixture()
def rubric_and_learner(db_session):
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
        return rub, learner

    return _make


def test_admin_creates_submission(client, auth_headers, rubric_and_learner):
    headers, admin = auth_headers(role="admin")
    rub, learner = rubric_and_learner(created_by=admin.id)
    response = client.post(f"/learners/{learner.id}/submissions", headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert body["learner_id"] == str(learner.id)
    assert body["rubric_id"] == str(rub.id)
    assert body["artifacts"] == []
    assert body["evaluation"] is None
    assert body["created_by"] == str(admin.id)


def test_evaluator_creates_submission_in_own_rubric(
    client, auth_headers, rubric_and_learner
):
    headers, evaluator = auth_headers(role="evaluator")
    _, learner = rubric_and_learner(created_by=evaluator.id)
    response = client.post(f"/learners/{learner.id}/submissions", headers=headers)
    assert response.status_code == 201


def test_evaluator_cannot_create_in_unowned_rubric(
    client, auth_headers, rubric_and_learner, make_user
):
    other_admin, _ = make_user(role="admin")
    _, learner = rubric_and_learner(created_by=other_admin.id)
    headers, _ = auth_headers(role="evaluator")
    response = client.post(f"/learners/{learner.id}/submissions", headers=headers)
    assert response.status_code == 404


def test_viewer_cannot_create_submission(
    client, auth_headers, rubric_and_learner
):
    headers, viewer = auth_headers(role="viewer")
    _, learner = rubric_and_learner(created_by=viewer.id)
    response = client.post(f"/learners/{learner.id}/submissions", headers=headers)
    assert response.status_code == 403


def test_unauthenticated_cannot_create(client, rubric_and_learner, make_user):
    other_admin, _ = make_user(role="admin")
    _, learner = rubric_and_learner(created_by=other_admin.id)
    response = client.post(f"/learners/{learner.id}/submissions")
    assert response.status_code == 401


def test_create_submission_for_unknown_learner_returns_404(client, auth_headers):
    headers, _ = auth_headers(role="admin")
    response = client.post(f"/learners/{uuid.uuid4()}/submissions", headers=headers)
    assert response.status_code == 404
