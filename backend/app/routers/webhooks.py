import hmac
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_db
from app.models import Evaluation, EvaluationScore, Submission
from app.routers.submissions import _build_detail
from app.schemas.submission import SubmissionDetailOut
from app.schemas.webhook import WebhookCallbackBody
from app.services.artifact_storage import (
    LocalArtifactStorage,
    get_artifact_storage,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

CALLBACK_API_KEY_HEADER = "X-API-Key"


def _verify_callback_api_key(
    x_api_key: str | None = Header(default=None, alias=CALLBACK_API_KEY_HEADER),
) -> None:
    """n8n authenticates each callback with a fixed shared secret in
    X-API-Key. Use a constant-time compare to avoid leaking the secret via
    timing differences."""
    expected = settings.callback_secret
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing callback API key",
        )


@router.post(
    "/n8n-callback",
    response_model=SubmissionDetailOut,
    dependencies=[Depends(_verify_callback_api_key)],
)
def n8n_callback(
    body: WebhookCallbackBody,
    db: Session = Depends(get_db),
    storage: LocalArtifactStorage = Depends(get_artifact_storage),
) -> SubmissionDetailOut:
    """Receive evaluation results from n8n. Auth is the X-API-Key header
    handled in the dependency above; correlation is by learner_id (each
    learner has at most one submission)."""
    submission = db.scalar(
        select(Submission).where(Submission.learner_id == body.learner_id)
    )
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No submission found for that learner",
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
        submission.error_message = (
            body.error_message or "n8n reported failure with no details"
        )

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
