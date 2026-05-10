import logging
import shutil
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Submission
from app.services.artifact_storage import LocalArtifactStorage

logger = logging.getLogger(__name__)

STUCK_ERROR_MESSAGE = "Evaluation timed out (no callback received)"


def cleanup_old_artifact_dirs(
    storage: LocalArtifactStorage,
    *,
    ttl_hours: int,
    now: datetime | None = None,
) -> dict[str, int]:
    """Delete subdirectories of the artifact root whose mtime is older than ttl_hours."""
    cutoff = (now or datetime.now(tz=UTC)) - timedelta(hours=ttl_hours)
    deleted = 0
    for path, mtime in storage.iter_submission_dirs():
        if mtime < cutoff:
            try:
                shutil.rmtree(path, ignore_errors=False)
                deleted += 1
                logger.warning(
                    "artifact dir cleanup: removed %s (mtime=%s)", path, mtime.isoformat()
                )
            except OSError as exc:
                logger.warning("artifact dir cleanup: failed to remove %s: %s", path, exc)
    logger.info("artifact dir cleanup complete; deleted=%d", deleted)
    return {"deleted": deleted}


def mark_stuck_submissions_failed(
    db: Session,
    *,
    stuck_after_minutes: int,
    now: datetime | None = None,
) -> dict[str, int]:
    """Flip processing submissions whose triggered_at is older than the threshold to failed.

    Disk artifacts are intentionally left for the artifact-age sweep so the two SPEC
    cleanup jobs stay independent.
    """
    current = now or datetime.now(tz=UTC)
    cutoff = current - timedelta(minutes=stuck_after_minutes)
    stuck = list(
        db.scalars(
            select(Submission).where(
                Submission.status == "processing",
                Submission.triggered_at.is_not(None),
                Submission.triggered_at < cutoff,
            )
        )
    )
    for submission in stuck:
        submission.status = "failed"
        submission.completed_at = current
        submission.error_message = STUCK_ERROR_MESSAGE
        logger.warning(
            "stuck-processing sweep: submission_id=%s flipped to failed (triggered_at=%s)",
            submission.id,
            submission.triggered_at.isoformat() if submission.triggered_at else None,
        )
    if stuck:
        db.commit()
    logger.info("stuck-processing sweep complete; failed=%d", len(stuck))
    return {"failed": len(stuck)}
