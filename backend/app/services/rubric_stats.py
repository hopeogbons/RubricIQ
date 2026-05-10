from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Learner, Submission


def compute_rubric_stats(db: Session, rubric_id: UUID) -> dict[str, int | float]:
    learner_count = db.scalar(
        select(func.count()).select_from(Learner).where(Learner.rubric_id == rubric_id)
    ) or 0
    submission_count = db.scalar(
        select(func.count())
        .select_from(Submission)
        .where(Submission.rubric_id == rubric_id)
    ) or 0
    completed_count = db.scalar(
        select(func.count())
        .select_from(Submission)
        .where(Submission.rubric_id == rubric_id, Submission.status == "complete")
    ) or 0
    completion_rate = (completed_count / submission_count) if submission_count else 0.0
    return {
        "learner_count": int(learner_count),
        "submission_count": int(submission_count),
        "completion_rate": float(completion_rate),
    }
