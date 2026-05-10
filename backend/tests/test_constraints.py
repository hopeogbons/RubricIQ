import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Learner, Rubric, Submission


def test_submission_status_check_rejects_invalid_value(db_session):
    rubric = Rubric(unique_name=f"rub-{uuid.uuid4()}", display_name="Rubric")
    db_session.add(rubric)
    db_session.flush()

    learner = Learner(rubric_id=rubric.id, full_name="Test Learner")
    db_session.add(learner)
    db_session.flush()

    submission = Submission(
        learner_id=learner.id,
        rubric_id=rubric.id,
        status="bogus",
    )
    db_session.add(submission)
    with pytest.raises(IntegrityError):
        db_session.flush()
