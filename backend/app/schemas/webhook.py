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
    """n8n -> RubricIQ callback. n8n authenticates with a fixed X-API-Key header
    that we verify against settings.callback_secret; correlation is by
    learner_id since each learner has at most one submission."""

    learner_id: UUID
    status: Literal["complete", "failed"]
    evaluation: WebhookCallbackEvaluation | None = None
    error_message: str | None = None
