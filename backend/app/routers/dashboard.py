from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_active_user, get_db, require_admin
from app.models import Rubric, User
from app.schemas.dashboard import DashboardStatsOut, RubricChartStatsOut
from app.services.access import rubric_scope_clause
from app.services.dashboard_stats import (
    compute_global_stats,
    compute_rubric_chart_stats,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsOut)
def get_global_stats(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return compute_global_stats(db)


@router.get("/rubrics/{rubric_id}/stats", response_model=RubricChartStatsOut)
def get_rubric_chart_stats(
    rubric_id: UUID,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Rubric).where(Rubric.id == rubric_id)
    clause = rubric_scope_clause(user)
    if clause is not None:
        stmt = stmt.where(clause)
    if db.scalar(stmt) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rubric not found"
        )
    return compute_rubric_chart_stats(db, rubric_id)
