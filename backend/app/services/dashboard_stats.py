from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Evaluation, EvaluationScore, Learner, Rubric, Submission

HISTOGRAM_BUCKETS = [
    "0-10%",
    "10-20%",
    "20-30%",
    "30-40%",
    "40-50%",
    "50-60%",
    "60-70%",
    "70-80%",
    "80-90%",
    "90-100%",
]


def _bucket_index(score: float, max_total: float) -> int:
    """Map a (score / max_total) ratio into 0..9. 100% falls into the top bucket."""
    if max_total <= 0:
        return 0
    pct = (score / max_total) * 100
    if pct >= 100:
        return 9
    if pct < 0:
        return 0
    return int(pct // 10)


def compute_global_stats(db: Session) -> dict[str, int | float]:
    total_rubrics = db.scalar(select(func.count()).select_from(Rubric)) or 0
    total_learners = db.scalar(select(func.count()).select_from(Learner)) or 0
    total_submissions = db.scalar(select(func.count()).select_from(Submission)) or 0
    completed = (
        db.scalar(
            select(func.count())
            .select_from(Submission)
            .where(Submission.status == "complete")
        )
        or 0
    )
    rate = (completed / total_submissions) if total_submissions else 0.0
    return {
        "total_rubrics": int(total_rubrics),
        "total_learners": int(total_learners),
        "total_submissions": int(total_submissions),
        "completion_rate": float(rate),
    }


def compute_rubric_chart_stats(db: Session, rubric_id: UUID) -> dict:
    """Aggregate evaluation data for the rubric detail charts.

    Only landed (status=complete with an evaluation row) submissions count
    toward the histogram, averages, and criterion breakdown.
    """
    rows = list(
        db.execute(
            select(Evaluation.total_score, Evaluation.max_total)
            .join(Submission, Submission.id == Evaluation.submission_id)
            .where(
                Submission.rubric_id == rubric_id,
                Submission.status == "complete",
                Evaluation.total_score.is_not(None),
                Evaluation.max_total.is_not(None),
            )
        )
    )

    distribution = [0] * len(HISTOGRAM_BUCKETS)
    total_sum = 0.0
    max_sum = 0.0
    counted = 0
    for total_score, max_total in rows:
        if total_score is None or max_total is None:
            continue
        score_f = float(total_score)
        max_f = float(max_total)
        if max_f <= 0:
            continue
        distribution[_bucket_index(score_f, max_f)] += 1
        total_sum += score_f
        max_sum += max_f
        counted += 1

    average_total = (total_sum / counted) if counted else None
    average_max = (max_sum / counted) if counted else None

    criterion_rows = list(
        db.execute(
            select(
                EvaluationScore.criterion,
                func.avg(EvaluationScore.score).label("avg_score"),
                func.avg(EvaluationScore.max_score).label("avg_max"),
                func.count().label("n"),
            )
            .join(Evaluation, Evaluation.id == EvaluationScore.evaluation_id)
            .join(Submission, Submission.id == Evaluation.submission_id)
            .where(
                Submission.rubric_id == rubric_id,
                Submission.status == "complete",
            )
            .group_by(EvaluationScore.criterion)
            .order_by(EvaluationScore.criterion)
        )
    )

    criterion_averages = [
        {
            "criterion": row.criterion,
            "average": float(row.avg_score) if row.avg_score is not None else 0.0,
            "max_score_average": float(row.avg_max) if row.avg_max is not None else 0.0,
            "count": int(row.n),
        }
        for row in criterion_rows
    ]

    return {
        "rubric_id": rubric_id,
        "average_total_score": average_total,
        "average_max_total": average_max,
        "score_distribution": [
            {"bucket": HISTOGRAM_BUCKETS[i], "count": distribution[i]}
            for i in range(len(HISTOGRAM_BUCKETS))
        ],
        "criterion_averages": criterion_averages,
    }
