from uuid import UUID

from pydantic import BaseModel


class DashboardStatsOut(BaseModel):
    total_rubrics: int
    total_learners: int
    total_submissions: int
    completion_rate: float


class HistogramBucket(BaseModel):
    bucket: str
    count: int


class CriterionAverage(BaseModel):
    criterion: str
    average: float
    max_score_average: float
    count: int


class RubricChartStatsOut(BaseModel):
    rubric_id: UUID
    average_total_score: float | None
    average_max_total: float | None
    score_distribution: list[HistogramBucket]
    criterion_averages: list[CriterionAverage]
