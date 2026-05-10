from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import get_current_active_user, get_db, require_admin
from app.models import Rubric, User
from app.schemas.rubric import (
    RubricCreate,
    RubricDetailOut,
    RubricOut,
    RubricUpdate,
)
from app.services.access import rubric_scope_clause
from app.services.rubric_stats import compute_rubric_stats

router = APIRouter(prefix="/rubrics", tags=["rubrics"])


def _get_rubric_in_scope(rubric_id: UUID, user: User, db: Session) -> Rubric:
    """Fetch a rubric the user is allowed to read; otherwise raise 404 to avoid
    leaking existence to out-of-scope users."""
    stmt = select(Rubric).where(Rubric.id == rubric_id)
    clause = rubric_scope_clause(user)
    if clause is not None:
        stmt = stmt.where(clause)
    rubric = db.scalar(stmt)
    if rubric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
    return rubric


@router.post("", response_model=RubricOut, status_code=status.HTTP_201_CREATED)
def create_rubric(
    body: RubricCreate,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Rubric:
    rubric = Rubric(
        unique_name=body.unique_name,
        display_name=body.display_name,
        description=body.description,
        google_sheet_id=body.google_sheet_id,
        google_drive_folder_path=body.google_drive_folder_path,
        created_by=user.id,
    )
    db.add(rubric)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A rubric with that unique_name already exists",
        ) from exc
    db.refresh(rubric)
    return rubric


@router.get("", response_model=list[RubricOut])
def list_rubrics(
    user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> list[Rubric]:
    stmt = select(Rubric).order_by(Rubric.created_at.desc())
    clause = rubric_scope_clause(user)
    if clause is not None:
        stmt = stmt.where(clause)
    return list(db.scalars(stmt))


@router.get("/{rubric_id}", response_model=RubricDetailOut)
def get_rubric(
    rubric_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> RubricDetailOut:
    rubric = _get_rubric_in_scope(rubric_id, user, db)
    stats = compute_rubric_stats(db, rubric.id)
    return RubricDetailOut(
        id=rubric.id,
        unique_name=rubric.unique_name,
        display_name=rubric.display_name,
        description=rubric.description,
        google_sheet_id=rubric.google_sheet_id,
        google_drive_folder_path=rubric.google_drive_folder_path,
        created_by=rubric.created_by,
        created_at=rubric.created_at,
        learner_count=stats["learner_count"],
        submission_count=stats["submission_count"],
        completion_rate=stats["completion_rate"],
    )


@router.patch("/{rubric_id}", response_model=RubricOut)
def update_rubric(
    rubric_id: UUID,
    body: RubricUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Rubric:
    """Updates mutable rubric fields. `unique_name` is intentionally excluded;
    it's the n8n key and changing it would orphan in-flight workflows."""
    rubric = db.get(Rubric, rubric_id)
    if rubric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(rubric, field, value)
    db.commit()
    db.refresh(rubric)
    return rubric


@router.delete("/{rubric_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rubric(
    rubric_id: UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    rubric = db.get(Rubric, rubric_id)
    if rubric is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found")
    db.delete(rubric)
    db.commit()
