import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models import Learner, Rubric
from app.tasks.cleanup import STUCK_ERROR_MESSAGE, mark_stuck_submissions_failed


@pytest.fixture()
def make_processing_submission(db_session, make_submission):
    """Build a submission, set it to a given status with a triggered_at offset."""
    counter = {"n": 0}

    def _make(*, status: str = "processing", triggered_minutes_ago: int | None = 60):
        counter["n"] += 1
        rub = Rubric(
            unique_name=f"r-{uuid.uuid4().hex[:8]}",
            display_name="R",
        )
        db_session.add(rub)
        db_session.flush()
        learner = Learner(rubric_id=rub.id, full_name="L")
        db_session.add(learner)
        db_session.flush()
        sub = make_submission(rub, learner=learner)
        sub.status = status
        if triggered_minutes_ago is not None:
            sub.triggered_at = datetime.now(tz=UTC) - timedelta(minutes=triggered_minutes_ago)
        else:
            sub.triggered_at = None
        db_session.flush()
        return sub

    return _make


def test_old_processing_submission_flips_to_failed(db_session, make_processing_submission):
    sub = make_processing_submission(triggered_minutes_ago=60)
    result = mark_stuck_submissions_failed(db_session, stuck_after_minutes=30)
    db_session.refresh(sub)
    assert result == {"failed": 1}
    assert sub.status == "failed"
    assert sub.error_message == STUCK_ERROR_MESSAGE
    assert sub.completed_at is not None


def test_recent_processing_submission_left_alone(db_session, make_processing_submission):
    sub = make_processing_submission(triggered_minutes_ago=10)
    result = mark_stuck_submissions_failed(db_session, stuck_after_minutes=30)
    db_session.refresh(sub)
    assert result == {"failed": 0}
    assert sub.status == "processing"


@pytest.mark.parametrize("status", ["draft", "complete", "failed"])
def test_non_processing_submissions_left_alone(
    db_session, make_processing_submission, status
):
    sub = make_processing_submission(status=status, triggered_minutes_ago=120)
    result = mark_stuck_submissions_failed(db_session, stuck_after_minutes=30)
    db_session.refresh(sub)
    assert result == {"failed": 0}
    assert sub.status == status


def test_processing_with_null_triggered_at_is_ignored(
    db_session, make_processing_submission
):
    sub = make_processing_submission(triggered_minutes_ago=None)
    result = mark_stuck_submissions_failed(db_session, stuck_after_minutes=30)
    db_session.refresh(sub)
    assert result == {"failed": 0}
    assert sub.status == "processing"


def test_now_parameter_overrides_clock(db_session, make_processing_submission):
    sub = make_processing_submission(triggered_minutes_ago=10)
    # Pretend it's much later: with now=+2h, the 10-min-ago submission is now 2h+10m old
    result = mark_stuck_submissions_failed(
        db_session,
        stuck_after_minutes=30,
        now=datetime.now(tz=UTC) + timedelta(hours=2),
    )
    db_session.refresh(sub)
    assert result == {"failed": 1}
    assert sub.status == "failed"
