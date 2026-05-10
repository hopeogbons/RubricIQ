import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.evaluation import Evaluation


class EvaluationScore(Base):
    __tablename__ = "evaluation_scores"
    __table_args__ = (Index("ix_evaluation_scores_evaluation_id", "evaluation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluations.id", ondelete="CASCADE"),
        nullable=False,
    )
    criterion: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float] = mapped_column(Numeric, nullable=False)
    max_score: Mapped[float] = mapped_column(Numeric, nullable=False)
    explanation: Mapped[str | None] = mapped_column(String, nullable=True)

    evaluation: Mapped["Evaluation"] = relationship(back_populates="scores")
