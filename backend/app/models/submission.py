import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.evaluation import Evaluation
    from app.models.learner import Learner
    from app.models.submission_artifact import SubmissionArtifact


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        CheckConstraint(
            "status in ('draft','processing','complete','failed')",
            name="submissions_status_check",
        ),
        Index("ix_submissions_rubric_id_status", "rubric_id", "status"),
        Index("ix_submissions_learner_id", "learner_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learners.id", ondelete="CASCADE"),
        nullable=False,
    )
    rubric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rubrics.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, server_default="draft", default="draft"
    )
    triggered_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    learner: Mapped["Learner"] = relationship(back_populates="submissions")
    evaluation: Mapped["Evaluation | None"] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
        single_parent=True,
        uselist=False,
        lazy="joined",
    )
    artifacts: Mapped[list["SubmissionArtifact"]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="SubmissionArtifact.created_at",
        lazy="selectin",
    )
