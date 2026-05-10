import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.db import SessionLocal
from app.services.artifact_storage import get_artifact_storage
from app.tasks.cleanup import (
    cleanup_old_artifact_dirs,
    mark_stuck_submissions_failed,
)

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_STARTUP_DELAY_SECONDS = 60


def _run_artifact_cleanup() -> None:
    storage = get_artifact_storage()
    try:
        cleanup_old_artifact_dirs(storage, ttl_hours=settings.artifact_ttl_hours)
    except Exception:
        logger.exception("artifact cleanup job raised")


def _run_stuck_sweep() -> None:
    db = SessionLocal()
    try:
        mark_stuck_submissions_failed(
            db, stuck_after_minutes=settings.stuck_after_minutes
        )
    except Exception:
        logger.exception("stuck-submission sweep raised")
    finally:
        db.close()


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    interval = IntervalTrigger(minutes=settings.cleanup_interval_minutes)
    first_fire = datetime.now() + timedelta(seconds=_STARTUP_DELAY_SECONDS)
    scheduler.add_job(
        _run_artifact_cleanup,
        trigger=interval,
        next_run_time=first_fire,
        id="artifact_dir_cleanup",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_stuck_sweep,
        trigger=interval,
        next_run_time=first_fire,
        id="stuck_submission_sweep",
        replace_existing=True,
    )
    return scheduler


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = build_scheduler()
    _scheduler.start()
    logger.info(
        "cleanup scheduler started (interval=%dm, ttl_hours=%d, stuck_after=%dm)",
        settings.cleanup_interval_minutes,
        settings.artifact_ttl_hours,
        settings.stuck_after_minutes,
    )


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("cleanup scheduler stopped")
