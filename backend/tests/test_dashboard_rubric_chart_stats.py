import uuid
from datetime import UTC, datetime

import pytest

from app.models import Evaluation, EvaluationScore, Learner, Rubric, Submission


@pytest.fixture()
def make_rubric(db_session):
    def _make(*, created_by=None) -> Rubric:
        rub = Rubric(
            unique_name=f"r-{uuid.uuid4().hex[:8]}",
            display_name="R",
            created_by=created_by,
        )
        db_session.add(rub)
        db_session.flush()
        return rub

    return _make


def _add_completed_submission(
    db,
    rubric: Rubric,
    *,
    total_score: float,
    max_total: float,
    criterion_scores: list[tuple[str, float, float]] | None = None,
) -> Submission:
    learner = Learner(rubric_id=rubric.id, full_name="L")
    db.add(learner)
    db.flush()
    sub = Submission(
        learner_id=learner.id,
        rubric_id=rubric.id,
        status="complete",
        completed_at=datetime.now(tz=UTC),
    )
    db.add(sub)
    db.flush()
    ev = Evaluation(submission_id=sub.id, total_score=total_score, max_total=max_total)
    db.add(ev)
    db.flush()
    for criterion, score, max_score in criterion_scores or []:
        db.add(
            EvaluationScore(
                evaluation_id=ev.id,
                criterion=criterion,
                score=score,
                max_score=max_score,
            )
        )
    db.flush()
    return sub


def test_rubric_chart_stats_buckets_scores_by_percentage(
    client, auth_headers, db_session, make_rubric
):
    headers, _ = auth_headers(role="admin")
    rub = make_rubric()
    # 5%, 35%, 95%, 100%, 75%
    for total, mx in [(5, 100), (35, 100), (95, 100), (100, 100), (15, 20)]:
        _add_completed_submission(db_session, rub, total_score=total, max_total=mx)
    db_session.flush()

    resp = client.get(f"/dashboard/rubrics/{rub.id}/stats", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    counts = {b["bucket"]: b["count"] for b in body["score_distribution"]}
    assert counts["0-10%"] == 1
    assert counts["30-40%"] == 1
    assert counts["70-80%"] == 1
    assert counts["90-100%"] == 2  # 95% lands in 90-100, 100% also lands there
    assert sum(counts.values()) == 5


def test_rubric_chart_stats_averages_total_and_criteria(
    client, auth_headers, db_session, make_rubric
):
    headers, _ = auth_headers(role="admin")
    rub = make_rubric()
    _add_completed_submission(
        db_session,
        rub,
        total_score=8,
        max_total=10,
        criterion_scores=[("Clarity", 4, 5), ("Depth", 4, 5)],
    )
    _add_completed_submission(
        db_session,
        rub,
        total_score=6,
        max_total=10,
        criterion_scores=[("Clarity", 3, 5), ("Depth", 3, 5)],
    )
    db_session.flush()

    resp = client.get(f"/dashboard/rubrics/{rub.id}/stats", headers=headers)
    body = resp.json()
    assert body["average_total_score"] == pytest.approx(7.0)
    assert body["average_max_total"] == pytest.approx(10.0)
    criterion_map = {c["criterion"]: c for c in body["criterion_averages"]}
    assert criterion_map["Clarity"]["average"] == pytest.approx(3.5)
    assert criterion_map["Clarity"]["max_score_average"] == pytest.approx(5.0)
    assert criterion_map["Clarity"]["count"] == 2
    assert criterion_map["Depth"]["average"] == pytest.approx(3.5)


def test_rubric_chart_stats_ignores_non_complete_submissions(
    client, auth_headers, db_session, make_rubric
):
    """Drafts, processing, and failed submissions don't count even if they have evaluations."""
    headers, _ = auth_headers(role="admin")
    rub = make_rubric()
    _add_completed_submission(
        db_session,
        rub,
        total_score=8,
        max_total=10,
        criterion_scores=[("Clarity", 4, 5)],
    )
    # Build a draft submission with an evaluation row that should be excluded.
    learner = Learner(rubric_id=rub.id, full_name="X")
    db_session.add(learner)
    db_session.flush()
    draft = Submission(learner_id=learner.id, rubric_id=rub.id, status="draft")
    db_session.add(draft)
    db_session.flush()
    ev = Evaluation(submission_id=draft.id, total_score=1, max_total=10)
    db_session.add(ev)
    db_session.flush()
    db_session.add(
        EvaluationScore(evaluation_id=ev.id, criterion="Clarity", score=1, max_score=5)
    )
    db_session.flush()

    resp = client.get(f"/dashboard/rubrics/{rub.id}/stats", headers=headers)
    body = resp.json()
    assert body["average_total_score"] == pytest.approx(8.0)
    assert body["criterion_averages"][0]["criterion"] == "Clarity"
    assert body["criterion_averages"][0]["count"] == 1


def test_rubric_chart_stats_empty_when_no_completed_submissions(
    client, auth_headers, make_rubric
):
    headers, _ = auth_headers(role="admin")
    rub = make_rubric()
    resp = client.get(f"/dashboard/rubrics/{rub.id}/stats", headers=headers)
    body = resp.json()
    assert body["average_total_score"] is None
    assert body["average_max_total"] is None
    assert sum(b["count"] for b in body["score_distribution"]) == 0
    assert body["criterion_averages"] == []


def test_rubric_chart_stats_404_for_unknown_rubric(client, auth_headers):
    headers, _ = auth_headers(role="admin")
    resp = client.get(f"/dashboard/rubrics/{uuid.uuid4()}/stats", headers=headers)
    assert resp.status_code == 404


def test_rubric_chart_stats_404_when_viewer_lacks_scope(
    client, auth_headers, make_rubric
):
    # Viewers have no rubric access via rubric_scope_clause unless explicitly granted.
    rub = make_rubric()
    headers, _ = auth_headers(role="viewer")
    resp = client.get(f"/dashboard/rubrics/{rub.id}/stats", headers=headers)
    assert resp.status_code == 404


def test_rubric_chart_stats_requires_authentication(client, make_rubric):
    rub = make_rubric()
    resp = client.get(f"/dashboard/rubrics/{rub.id}/stats")
    assert resp.status_code == 401
