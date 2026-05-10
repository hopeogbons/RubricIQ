import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.submission import Submission


class Learner(Base):
    __tablename__ = "learners"
    __table_args__ = (
        UniqueConstraint("rubric_id", "email", name="learners_rubric_id_email_key"),
        Index("ix_learners_rubric_id", "rubric_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rubric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rubrics.id", ondelete="CASCADE"),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    cohort: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="learner",
        cascade="all, delete-orphan",
        order_by="Submission.created_at.desc()",
        lazy="selectin",
    )
