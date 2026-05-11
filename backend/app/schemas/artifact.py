from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

ArtifactType = Literal["loom", "gdrive_video", "github", "screenshot", "text"]
LinkArtifactType = Literal["loom", "gdrive_video", "github"]
FileArtifactType = Literal["screenshot"]

# Maximum length of a text-artifact value, defensive cap to keep abusive
# payloads out of the trigger body that we forward to n8n.
TEXT_VALUE_MAX_LEN = 50_000


class ArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    submission_id: UUID
    type: ArtifactType
    filename: str | None
    external_url: str | None
    text_value: str | None
    size_bytes: int | None
    created_at: datetime


class ArtifactLinkIn(BaseModel):
    type: LinkArtifactType
    url: HttpUrl


class ArtifactLinksCreate(BaseModel):
    links: list[ArtifactLinkIn] = Field(min_length=1, max_length=20)


class ArtifactTextCreate(BaseModel):
    value: str = Field(min_length=1, max_length=TEXT_VALUE_MAX_LEN)
