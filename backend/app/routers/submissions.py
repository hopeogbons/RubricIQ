import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import (
    get_current_active_user,
    get_db,
    require_admin_or_evaluator,
)
from app.models import Learner, Rubric, Submission, SubmissionArtifact, User
from app.schemas.artifact import ArtifactOut
from app.schemas.evaluation import EvaluationOut
from app.schemas.submission import SubmissionDetailOut, SubmissionStatusOut
from app.services.access import rubric_scope_clause
from app.services.artifact_token import issue_artifact_token
from app.services.n8n_service import N8nClient, N8nTriggerError, get_n8n_client

logger = logging.getLogger(__name__)

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
    """Create the learner's submission. A learner has at most one submission; if
    one already exists, return it instead of erroring so the caller can resume
    the existing draft or re-evaluate."""
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

    existing = db.scalar(
        select(Submission).where(Submission.learner_id == learner.id)
    )
    if existing is not None:
        return _build_detail(existing)

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


def _build_trigger_payload(submission: Submission, rubric: Rubric | None) -> dict:
    """Match the n8n trigger contract: a flat top-level body with the artifact
    set the workflow understands. URL artifacts share the same `url` key; text
    artifacts carry their content in `value` instead."""
    base = settings.public_api_base_url.rstrip("/")
    artifacts: list[dict] = []
    for a in submission.artifacts:
        if a.type == "screenshot":
            token = issue_artifact_token(submission.id, a.filename or "")
            artifacts.append({"type": "screenshot", "url": f"{base}/artifacts/{token}"})
        elif a.type == "text":
            artifacts.append({"type": "text", "value": a.text_value or ""})
        else:
            artifacts.append({"type": a.type, "url": a.external_url})

    return {
        "learner_id": str(submission.learner.id),
        "assessment_id": rubric.unique_name if rubric else None,
        "cohort": submission.learner.cohort,
        "artifacts": artifacts,
    }


@router.post("/{submission_id}/evaluate", response_model=SubmissionDetailOut)
def evaluate_submission(
    submission_id: UUID,
    user: User = Depends(require_admin_or_evaluator),
    db: Session = Depends(get_db),
    n8n: N8nClient = Depends(get_n8n_client),
) -> SubmissionDetailOut:
    """Trigger an evaluation. Allowed when the submission is in `draft`,
    `complete`, or `failed`; calling on `complete` or `failed` clears the
    prior evaluation row so the new result replaces it. `processing` rejects
    with 409 to avoid two concurrent n8n workflows for one learner."""
    submission = _submission_in_scope(submission_id, user, db)

    if submission.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Submission is already processing",
        )

    artifact_count = db.scalar(
        select(SubmissionArtifact.id)
        .where(SubmissionArtifact.submission_id == submission.id)
        .limit(1)
    )
    if not artifact_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot evaluate a submission with no artifacts",
        )

    rubric = db.get(Rubric, submission.rubric_id)
    payload = _build_trigger_payload(submission, rubric)

    try:
        n8n.trigger(payload)
    except N8nTriggerError as exc:
        logger.warning("n8n trigger failed for submission_id=%s: %s", submission.id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach n8n; submission left in its prior state",
        ) from exc

    # Re-evaluation: wipe the prior evaluation row (cascades will remove
    # EvaluationScore rows) so the upcoming callback writes a fresh one.
    if submission.evaluation is not None:
        db.delete(submission.evaluation)
        db.flush()
    submission.status = "processing"
    submission.triggered_at = datetime.now(tz=UTC)
    submission.completed_at = None
    submission.error_message = None
    db.commit()
    db.refresh(submission)
    return _build_detail(submission)
