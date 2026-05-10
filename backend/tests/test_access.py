"""Unit tests for the rubric_scope_clause helper.

Exercises the predicate by executing it in a real query rather than asserting
on the SQLAlchemy AST - more robust to dialect differences and clearly
verifies behavior end-to-end.
"""
import uuid

from sqlalchemy import select

from app.models import Learner, Rubric, Submission, User
from app.services.access import rubric_scope_clause


def _user(role):
    return User(id=uuid.uuid4(), email=f"{role}@example.com", password_hash="x", role=role)


def test_admin_clause_is_none_meaning_no_filter():
    assert rubric_scope_clause(_user("admin")) is None
    assert rubric_scope_clause(_user("superadmin")) is None


def _u(role, email):
    return User(id=uuid.uuid4(), email=email, password_hash="x", role=role)


def test_evaluator_sees_own_and_submission_rubrics(db_session):
    creator = _u("admin", "creator@example.com")
    evaluator = _u("evaluator", "ev@example.com")
    db_session.add_all([creator, evaluator])
    db_session.flush()

    own_name = f"own-{uuid.uuid4().hex[:6]}"
    sub_name = f"sub-{uuid.uuid4().hex[:6]}"
    hid_name = f"hid-{uuid.uuid4().hex[:6]}"
    own = Rubric(unique_name=own_name, display_name="Own", created_by=evaluator.id)
    via_submission = Rubric(
        unique_name=sub_name, display_name="Via Sub", created_by=creator.id
    )
    invisible = Rubric(
        unique_name=hid_name, display_name="Hidden", created_by=creator.id
    )
    db_session.add_all([own, via_submission, invisible])
    db_session.flush()

    learner = Learner(rubric_id=via_submission.id, full_name="L")
    db_session.add(learner)
    db_session.flush()
    db_session.add(
        Submission(learner_id=learner.id, rubric_id=via_submission.id, created_by=evaluator.id)
    )
    db_session.flush()

    clause = rubric_scope_clause(evaluator)
    visible_ids = set(db_session.scalars(select(Rubric.id).where(clause)).all())
    assert own.id in visible_ids
    assert via_submission.id in visible_ids
    assert invisible.id not in visible_ids


def test_viewer_sees_only_own(db_session):
    creator = _u("admin", "c@example.com")
    viewer = _u("viewer", "v@example.com")
    db_session.add_all([creator, viewer])
    db_session.flush()

    own_name = f"own-{uuid.uuid4().hex[:6]}"
    other_name = f"oth-{uuid.uuid4().hex[:6]}"
    own = Rubric(unique_name=own_name, display_name="Own", created_by=viewer.id)
    other = Rubric(unique_name=other_name, display_name="Oth", created_by=creator.id)
    db_session.add_all([own, other])
    db_session.flush()

    clause = rubric_scope_clause(viewer)
    visible_ids = set(db_session.scalars(select(Rubric.id).where(clause)).all())
    assert own.id in visible_ids
    assert other.id not in visible_ids


def test_unknown_role_falls_back_to_viewer_semantics():
    user = _user("evaluator-trainee")  # not in our role set
    clause = rubric_scope_clause(user)
    assert clause is not None
    # The fallback predicate is created_by == user.id; we just confirm it's a clause object.
    assert "created_by" in str(clause).lower()
