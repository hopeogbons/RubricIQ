import uuid

import pytest

from app.models import Learner, Rubric


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


def test_admin_adds_learner(client, auth_headers, make_rubric):
    headers, admin = auth_headers(role="admin")
    rub = make_rubric(created_by=admin.id)
    response = client.post(
        f"/rubrics/{rub.id}/learners",
        headers=headers,
        json={"full_name": "Jane", "email": "jane@example.com", "cohort": "c1"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["full_name"] == "Jane"
    assert body["email"] == "jane@example.com"
    assert body["rubric_id"] == str(rub.id)


def test_evaluator_adds_learner_to_own_rubric(client, auth_headers, make_rubric):
    headers, evaluator = auth_headers(role="evaluator")
    rub = make_rubric(created_by=evaluator.id)
    response = client.post(
        f"/rubrics/{rub.id}/learners",
        headers=headers,
        json={"full_name": "Eve"},
    )
    assert response.status_code == 201


def test_evaluator_cannot_add_learner_to_unowned_rubric(
    client, auth_headers, make_user, make_rubric
):
    other_admin, _ = make_user(role="admin")
    rub = make_rubric(created_by=other_admin.id)
    eval_h, _ = auth_headers(role="evaluator")
    response = client.post(
        f"/rubrics/{rub.id}/learners", headers=eval_h, json={"full_name": "X"}
    )
    assert response.status_code == 404


def test_viewer_cannot_add_learner(client, auth_headers, make_rubric):
    headers, viewer = auth_headers(role="viewer")
    rub = make_rubric(created_by=viewer.id)
    response = client.post(
        f"/rubrics/{rub.id}/learners", headers=headers, json={"full_name": "X"}
    )
    assert response.status_code == 403


def test_unauthenticated_cannot_add_learner(client, make_rubric, make_user):
    other_admin, _ = make_user(role="admin")
    rub = make_rubric(created_by=other_admin.id)
    response = client.post(f"/rubrics/{rub.id}/learners", json={"full_name": "X"})
    assert response.status_code == 401


def test_duplicate_learner_email_in_rubric_returns_400(client, auth_headers, make_rubric):
    headers, admin = auth_headers(role="admin")
    rub = make_rubric(created_by=admin.id)
    p = {"full_name": "A", "email": "dup@example.com"}
    assert client.post(f"/rubrics/{rub.id}/learners", headers=headers, json=p).status_code == 201
    response = client.post(f"/rubrics/{rub.id}/learners", headers=headers, json=p)
    assert response.status_code == 400


def test_admin_deletes_learner(client, auth_headers, make_rubric, db_session):
    headers, admin = auth_headers(role="admin")
    rub = make_rubric(created_by=admin.id)
    learner = Learner(rubric_id=rub.id, full_name="Jane")
    db_session.add(learner)
    db_session.flush()

    response = client.delete(f"/learners/{learner.id}", headers=headers)
    assert response.status_code == 204
    assert client.get(f"/learners/{learner.id}", headers=headers).status_code == 404


def test_evaluator_cannot_delete_learner(client, auth_headers, make_rubric, db_session):
    a_h, admin = auth_headers(role="admin")
    rub = make_rubric(created_by=admin.id)
    learner = Learner(rubric_id=rub.id, full_name="Jane")
    db_session.add(learner)
    db_session.flush()

    eval_h, _ = auth_headers(role="evaluator")
    response = client.delete(f"/learners/{learner.id}", headers=eval_h)
    assert response.status_code == 403


def test_delete_unknown_learner_returns_404(client, auth_headers):
    headers, _ = auth_headers(role="admin")
    response = client.delete(f"/learners/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404
