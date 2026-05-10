import uuid
from datetime import UTC, datetime

from app.models import Evaluation, Learner, Rubric


def _seed_rubric_with_submissions(db, *, statuses: list[str]) -> Rubric:
    rub = Rubric(unique_name=f"r-{uuid.uuid4().hex[:8]}", display_name="R")
    db.add(rub)
    db.flush()
    learner = Learner(rubric_id=rub.id, full_name="L")
    db.add(learner)
    db.flush()
    from app.models import Submission

    for status in statuses:
        db.add(
            Submission(
                learner_id=learner.id,
                rubric_id=rub.id,
                status=status,
                completed_at=datetime.now(tz=UTC) if status == "complete" else None,
            )
        )
    db.flush()
    return rub


def test_global_stats_zero_when_empty(client, auth_headers):
    headers, _ = auth_headers(role="admin")
    resp = client.get("/dashboard/stats", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {
        "total_rubrics": 0,
        "total_learners": 0,
        "total_submissions": 0,
        "completion_rate": 0.0,
    }


def test_global_stats_counts_and_completion_rate(client, auth_headers, db_session):
    headers, _ = auth_headers(role="superadmin")
    _seed_rubric_with_submissions(
        db_session, statuses=["complete", "complete", "processing", "failed"]
    )
    _seed_rubric_with_submissions(db_session, statuses=["complete"])
    db_session.flush()

    resp = client.get("/dashboard/stats", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_rubrics"] == 2
    assert body["total_learners"] == 2
    assert body["total_submissions"] == 5
    # 3 of 5 complete -> 0.6
    assert body["completion_rate"] == 0.6


def test_global_stats_requires_admin(client, auth_headers):
    for role in ("viewer", "evaluator"):
        headers, _ = auth_headers(role=role)
        resp = client.get("/dashboard/stats", headers=headers)
        assert resp.status_code == 403, f"{role}: {resp.text}"


def test_global_stats_requires_authentication(client):
    resp = client.get("/dashboard/stats")
    assert resp.status_code == 401


def test_inactive_admin_blocked(client, auth_headers):
    headers, _ = auth_headers(role="admin", is_active=False)
    resp = client.get("/dashboard/stats", headers=headers)
    assert resp.status_code == 403


def test_evaluation_rows_ignored_for_global_stats(client, auth_headers, db_session):
    """Global stats look at submissions, not evaluations; rate is based on status only."""
    from app.models import Submission
    from sqlalchemy import select

    headers, _ = auth_headers(role="admin")
    rub = _seed_rubric_with_submissions(db_session, statuses=["complete"])
    sub = db_session.scalar(select(Submission).where(Submission.rubric_id == rub.id))
    db_session.add(
        Evaluation(submission_id=sub.id, total_score=5, max_total=10)
    )
    db_session.flush()

    resp = client.get("/dashboard/stats", headers=headers)
    body = resp.json()
    assert body["total_submissions"] == 1
    assert body["completion_rate"] == 1.0
