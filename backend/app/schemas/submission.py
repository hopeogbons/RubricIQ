from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.submission import Submission


class SubmissionSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    triggered_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime
    total_score: float | None
    max_total: float | None
    evaluated_at: datetime | None

    @classmethod
    def from_submission(cls, submission: Submission) -> "SubmissionSummaryOut":
        evaluation = submission.evaluation
        total_score: float | None = None
        max_total: float | None = None
        if evaluation is not None:
            if evaluation.total_score is not None:
                total_score = float(evaluation.total_score)
            if evaluation.max_total is not None:
                max_total = float(evaluation.max_total)
        return cls(
            id=submission.id,
            status=submission.status,
            triggered_at=submission.triggered_at,
            completed_at=submission.completed_at,
            error_message=submission.error_message,
            created_at=submission.created_at,
            total_score=total_score,
            max_total=max_total,
            evaluated_at=evaluation.evaluated_at if evaluation else None,
        )
