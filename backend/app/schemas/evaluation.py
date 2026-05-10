from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EvaluationScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    criterion: str
    score: float
    max_score: float
    explanation: str | None


class EvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    submission_id: UUID
    total_score: float | None
    max_total: float | None
    evaluated_at: datetime
    scores: list[EvaluationScoreOut] = []
