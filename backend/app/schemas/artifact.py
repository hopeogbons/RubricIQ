from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

ArtifactType = Literal["video_file", "screenshot", "video_link", "github_link"]
LinkArtifactType = Literal["video_link", "github_link"]
FileArtifactType = Literal["video_file", "screenshot"]


class ArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    submission_id: UUID
    type: ArtifactType
    filename: str | None
    external_url: str | None
    size_bytes: int | None
    created_at: datetime


class ArtifactLinkIn(BaseModel):
    type: LinkArtifactType
    url: HttpUrl


class ArtifactLinksCreate(BaseModel):
    links: list[ArtifactLinkIn] = Field(min_length=1, max_length=20)
