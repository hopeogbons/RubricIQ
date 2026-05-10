from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import (
    get_current_active_user,
    get_db,
    require_admin,
    require_admin_or_evaluator,
)
from app.models import Learner, Rubric, User
from app.routers.rubrics import _get_rubric_in_scope
from app.schemas.learner import LearnerCreate, LearnerDetailOut, LearnerOut
from app.schemas.submission import SubmissionSummaryOut
from app.services.access import rubric_scope_clause

nested_router = APIRouter(prefix="/rubrics/{rubric_id}/learners", tags=["learners"])
flat_router = APIRouter(prefix="/learners", tags=["learners"])


@nested_router.post("", response_model=LearnerOut, status_code=status.HTTP_201_CREATED)
def create_learner(
    rubric_id: UUID,
    body: LearnerCreate,
    user: User = Depends(require_admin_or_evaluator),
    db: Session = Depends(get_db),
) -> Learner:
    # Confirm rubric exists and is in the caller's scope; 404 otherwise.
    _get_rubric_in_scope(rubric_id, user, db)
    learner = Learner(
        rubric_id=rubric_id,
        full_name=body.full_name,
        email=body.email,
        cohort=body.cohort,
    )
    db.add(learner)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A learner with that email already exists in this rubric",
        ) from exc
    db.refresh(learner)
    return learner


@nested_router.get("", response_model=list[LearnerOut])
def list_learners(
    rubric_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[Learner]:
    _get_rubric_in_scope(rubric_id, user, db)
    return list(
        db.scalars(
            select(Learner)
            .where(Learner.rubric_id == rubric_id)
            .order_by(Learner.created_at.desc())
        )
    )


@flat_router.get("/{learner_id}", response_model=LearnerDetailOut)
def get_learner(
    learner_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> LearnerDetailOut:
    learner = db.get(Learner, learner_id)
    if learner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found")

    # Apply parent rubric scope; 404 if out of scope.
    clause = rubric_scope_clause(user)
    rubric_query = select(Rubric.id).where(Rubric.id == learner.rubric_id)
    if clause is not None:
        rubric_query = rubric_query.where(clause)
    if db.scalar(rubric_query) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found")

    return LearnerDetailOut(
        id=learner.id,
        rubric_id=learner.rubric_id,
        full_name=learner.full_name,
        email=learner.email,
        cohort=learner.cohort,
        created_at=learner.created_at,
        submissions=[SubmissionSummaryOut.from_submission(s) for s in learner.submissions],
    )


@flat_router.delete("/{learner_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_learner(
    learner_id: UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    learner = db.get(Learner, learner_id)
    if learner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found")
    db.delete(learner)
    db.commit()
