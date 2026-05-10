from sqlalchemy import ColumnElement, or_, select

from app.models import Rubric, Submission, User


def rubric_scope_clause(user: User) -> ColumnElement[bool] | None:
    """Build the role-based read scope predicate for the rubrics table.

    Returns None when the user sees everything (admin / superadmin); otherwise
    returns a SQLAlchemy boolean expression suitable for `select(Rubric).where(...)`.

    - admin / superadmin: full visibility (None).
    - evaluator: rubrics they created OR rubrics where they own a submission.
    - viewer (and any unrecognized role): rubrics they created.
    """
    if user.role in ("admin", "superadmin"):
        return None
    if user.role == "evaluator":
        return or_(
            Rubric.created_by == user.id,
            Rubric.id.in_(
                select(Submission.rubric_id).where(Submission.created_by == user.id)
            ),
        )
    return Rubric.created_by == user.id
