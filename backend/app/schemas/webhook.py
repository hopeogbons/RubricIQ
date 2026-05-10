from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WebhookCallbackScore(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    criterion: str
    score: float
    max_score: float = Field(alias="max")
    explanation: str | None = None


class WebhookCallbackEvaluation(BaseModel):
    total_score: float
    max_total: float
    scores: list[WebhookCallbackScore] = Field(default_factory=list)


class WebhookCallbackBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    submission_id: UUID
    callback_token: str
    status: Literal["complete", "failed"]
    evaluation: WebhookCallbackEvaluation | None = None
    error: str | None = None
