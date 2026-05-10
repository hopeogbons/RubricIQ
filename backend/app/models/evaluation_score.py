import uuid

from sqlalchemy import ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


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
