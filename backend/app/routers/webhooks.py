import logging
from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import Evaluation, EvaluationScore, Submission
from app.routers.submissions import _build_detail
from app.schemas.submission import SubmissionDetailOut
from app.schemas.webhook import WebhookCallbackBody
from app.services.artifact_storage import (
    LocalArtifactStorage,
    get_artifact_storage,
)
from app.services.callback_token import decode_callback_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/n8n-callback", response_model=SubmissionDetailOut)
def n8n_callback(
    body: WebhookCallbackBody,
    db: Session = Depends(get_db),
    storage: LocalArtifactStorage = Depends(get_artifact_storage),
) -> SubmissionDetailOut:
    """Receive evaluation results from n8n. The token in the body is the auth;
    no FastAPI user session is required (or possible)."""
    try:
        token_submission_id = decode_callback_token(body.callback_token)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired callback token"
        ) from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid callback token payload"
        ) from exc

    if token_submission_id != body.submission_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not match submission",
        )

    submission = db.get(Submission, body.submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )

    # Idempotent: if the submission is already terminal, return its current state.
    if submission.status in {"complete", "failed"}:
        logger.info(
            "Idempotent callback for already-%s submission_id=%s",
            submission.status,
            submission.id,
        )
        return _build_detail(submission)

    now = datetime.now(tz=UTC)
    if body.status == "complete":
        if body.evaluation is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="status=complete requires an evaluation payload",
            )
        evaluation = Evaluation(
            submission_id=submission.id,
            total_score=body.evaluation.total_score,
            max_total=body.evaluation.max_total,
            raw_response=body.model_dump(by_alias=True, mode="json"),
        )
        db.add(evaluation)
        db.flush()
        for score in body.evaluation.scores:
            db.add(
                EvaluationScore(
                    evaluation_id=evaluation.id,
                    criterion=score.criterion,
                    score=score.score,
                    max_score=score.max_score,
                    explanation=score.explanation,
                )
            )
        submission.status = "complete"
        submission.completed_at = now
        submission.error_message = None
    else:
        # status == "failed"
        submission.status = "failed"
        submission.completed_at = now
        submission.error_message = body.error or "n8n reported failure with no details"

    db.commit()
    db.refresh(submission)

    # Per SPEC: delete the artifacts directory on either outcome. Best effort.
    try:
        storage.delete_submission_dir(submission.id)
    except OSError as exc:
        logger.warning(
            "artifact dir cleanup failed for submission_id=%s: %s", submission.id, exc
        )

    return _build_detail(submission)
