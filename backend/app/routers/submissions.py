from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import (
    get_current_active_user,
    get_db,
    require_admin_or_evaluator,
)
from app.models import Learner, Rubric, Submission, User
from app.schemas.artifact import ArtifactOut
from app.schemas.evaluation import EvaluationOut
from app.schemas.submission import SubmissionDetailOut, SubmissionStatusOut
from app.services.access import rubric_scope_clause

router = APIRouter(prefix="/submissions", tags=["submissions"])
nested_router = APIRouter(prefix="/learners/{learner_id}/submissions", tags=["submissions"])


def _submission_in_scope(
    submission_id: UUID, user: User, db: Session
) -> Submission:
    """Fetch a submission whose parent rubric is visible to the user, else 404."""
    stmt = (
        select(Submission)
        .join(Rubric, Rubric.id == Submission.rubric_id)
        .where(Submission.id == submission_id)
    )
    clause = rubric_scope_clause(user)
    if clause is not None:
        stmt = stmt.where(clause)
    sub = db.scalar(stmt)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return sub


def _build_detail(submission: Submission) -> SubmissionDetailOut:
    return SubmissionDetailOut(
        id=submission.id,
        learner_id=submission.learner_id,
        rubric_id=submission.rubric_id,
        status=submission.status,
        triggered_at=submission.triggered_at,
        completed_at=submission.completed_at,
        error_message=submission.error_message,
        created_by=submission.created_by,
        created_at=submission.created_at,
        artifacts=[ArtifactOut.model_validate(a) for a in submission.artifacts],
        evaluation=EvaluationOut.model_validate(submission.evaluation)
        if submission.evaluation
        else None,
    )


@nested_router.post("", response_model=SubmissionDetailOut, status_code=status.HTTP_201_CREATED)
def create_submission(
    learner_id: UUID,
    user: User = Depends(require_admin_or_evaluator),
    db: Session = Depends(get_db),
) -> SubmissionDetailOut:
    learner = db.get(Learner, learner_id)
    if learner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found")

    # Enforce the parent-rubric scope just like creating a learner does.
    clause = rubric_scope_clause(user)
    rubric_q = select(Rubric.id).where(Rubric.id == learner.rubric_id)
    if clause is not None:
        rubric_q = rubric_q.where(clause)
    if db.scalar(rubric_q) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found")

    submission = Submission(
        learner_id=learner.id,
        rubric_id=learner.rubric_id,
        status="draft",
        created_by=user.id,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return _build_detail(submission)


@router.get("/{submission_id}", response_model=SubmissionDetailOut)
def get_submission(
    submission_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SubmissionDetailOut:
    submission = _submission_in_scope(submission_id, user, db)
    return _build_detail(submission)


@router.get("/{submission_id}/status", response_model=SubmissionStatusOut)
def get_submission_status(
    submission_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SubmissionStatusOut:
    submission = _submission_in_scope(submission_id, user, db)
    return SubmissionStatusOut.from_submission(submission)
