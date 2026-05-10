import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.evaluation_score import EvaluationScore
    from app.models.submission import Submission


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    total_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    max_total: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    submission: Mapped["Submission"] = relationship(back_populates="evaluation")
    scores: Mapped[list["EvaluationScore"]] = relationship(
        back_populates="evaluation",
        cascade="all, delete-orphan",
        order_by="EvaluationScore.criterion",
        lazy="selectin",
    )
