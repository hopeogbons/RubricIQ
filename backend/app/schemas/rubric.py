from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

UNIQUE_NAME_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class RubricCreate(BaseModel):
    unique_name: str = Field(min_length=1, max_length=100, pattern=UNIQUE_NAME_PATTERN)
    display_name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    google_sheet_id: str | None = Field(default=None, max_length=200)
    google_drive_folder_path: str | None = Field(default=None, max_length=500)


class RubricUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    google_sheet_id: str | None = Field(default=None, max_length=200)
    google_drive_folder_path: str | None = Field(default=None, max_length=500)


class RubricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    unique_name: str
    display_name: str
    description: str | None
    google_sheet_id: str | None
    google_drive_folder_path: str | None
    created_by: UUID | None
    created_at: datetime


class RubricDetailOut(RubricOut):
    learner_count: int
    submission_count: int
    completion_rate: float
