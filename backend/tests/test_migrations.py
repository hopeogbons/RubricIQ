from sqlalchemy import create_engine, text

EXPECTED_TABLES = {
    "users",
    "rubrics",
    "learners",
    "submissions",
    "submission_artifacts",
    "evaluations",
    "evaluation_scores",
}


def test_all_tables_present(database_url):
    engine = create_engine(database_url, future=True)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        ).all()
    names = {r[0] for r in rows}
    missing = EXPECTED_TABLES - names
    assert not missing, f"Missing tables: {missing}"


def test_submissions_status_check_constraint_present(database_url):
    engine = create_engine(database_url, future=True)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT constraint_name FROM information_schema.table_constraints "
                "WHERE table_name = 'submissions' AND constraint_type = 'CHECK'"
            )
        ).all()
    names = {r[0] for r in rows}
    assert "submissions_status_check" in names


def test_indexes_present(database_url):
    engine = create_engine(database_url, future=True)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")
        ).all()
    names = {r[0] for r in rows}
    assert "ix_learners_rubric_id" in names
    assert "ix_submissions_rubric_id_status" in names
    assert "ix_submissions_learner_id" in names
    assert "ix_evaluation_scores_evaluation_id" in names
