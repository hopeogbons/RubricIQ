from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.submission import SubmissionSummaryOut


class LearnerCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    cohort: str | None = Field(default=None, max_length=100)


class LearnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rubric_id: UUID
    full_name: str
    email: EmailStr | None
    cohort: str | None
    created_at: datetime


class LearnerDetailOut(LearnerOut):
    submissions: list[SubmissionSummaryOut]
