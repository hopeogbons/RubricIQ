import os
import shutil
import tempfile
from collections.abc import Generator
from datetime import UTC
from typing import Any

import pytest
from pytest_postgresql import factories
from pytest_postgresql.janitor import DatabaseJanitor

PG_BIN = "/usr/local/opt/postgresql@18/bin"
if os.path.isdir(PG_BIN):
    os.environ["PATH"] = f"{PG_BIN}:{os.environ.get('PATH', '')}"

# Settings reads these on first import of app.config; set them before any app import.
# DATABASE_URL is a placeholder so collection-time Settings() validation passes; the
# database_url fixture overrides it (and rebinds app.db) once the real test DB exists.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://placeholder/placeholder")
os.environ.setdefault("JWT_SECRET", "test-secret-32-bytes-minimum-for-hs256-rfc7518")
os.environ.setdefault("JWT_EXPIRES_MINUTES", "60")
os.environ.setdefault("SUPERADMIN_EMAIL", "seeded-admin@example.com")
os.environ.setdefault("SUPERADMIN_PASSWORD", "seeded-admin-pw")
os.environ.setdefault("FRONTEND_BASE_URL", "http://localhost:5173")
os.environ.setdefault(
    "ARTIFACT_SIGNING_SECRET", "test-artifact-secret-32-bytes-minimum-distinct-from-jwt"
)
_TEST_ARTIFACT_DIR = tempfile.mkdtemp(prefix="rubriciq-test-artifacts-")
os.environ.setdefault("ARTIFACT_DIR", _TEST_ARTIFACT_DIR)
# Smaller test limits keep size-limit tests cheap (10 KB / 50 KB).
os.environ.setdefault("MAX_FILE_BYTES", str(10 * 1024))
os.environ.setdefault("MAX_SUBMISSION_BYTES", str(50 * 1024))
# RESEND_API_KEY intentionally unset; tests override the email client dependency.

_pg_executable = shutil.which("pg_ctl") or f"{PG_BIN}/pg_ctl"

postgresql_proc = factories.postgresql_proc(executable=_pg_executable, port=None)


def _build_database_url(host: str, port: int, user: str, password: str, dbname: str) -> str:
    auth = f"{user}:{password}" if password else user
    return f"postgresql+psycopg://{auth}@{host}:{port}/{dbname}"


@pytest.fixture(scope="session")
def database_url(postgresql_proc) -> Generator[str, None, None]:
    """Create a dedicated test DB on the ephemeral pytest-postgresql cluster,
    point app.config.settings at it, run alembic upgrade head, and yield the URL."""
    dbname = "rubriciq_test"
    janitor = DatabaseJanitor(
        user=postgresql_proc.user,
        host=postgresql_proc.host,
        port=postgresql_proc.port,
        dbname=dbname,
        version=postgresql_proc.version,
        password=postgresql_proc.password,
    )
    janitor.init()
    url = _build_database_url(
        postgresql_proc.host,
        postgresql_proc.port,
        postgresql_proc.user,
        postgresql_proc.password or "",
        dbname,
    )
    os.environ["DATABASE_URL"] = url

    # Point the already-instantiated Settings singleton at the real test DB,
    # then rebind app.db.engine and SessionLocal so production code paths
    # (lifespan seed, get_db) use the test DB instead of the placeholder.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.db as app_db
    from app.config import settings as app_settings

    app_settings.database_url = url
    app_db.engine = create_engine(url, pool_pre_ping=True, future=True)
    app_db.SessionLocal = sessionmaker(
        bind=app_db.engine, autoflush=False, autocommit=False, future=True
    )

    from alembic.config import Config

    from alembic import command

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")

    yield url

    janitor.drop()


@pytest.fixture()
def db_session(database_url):
    """Per-test SQLAlchemy session bound to a SAVEPOINT so changes roll back."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(database_url, future=True)
    connection = engine.connect()
    transaction = connection.begin()

    SessionLocal = sessionmaker(
        bind=connection, autoflush=False, autocommit=False, future=True
    )
    session = SessionLocal()

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        nonlocal nested
        if trans.nested and not trans._parent.nested:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
        engine.dispose()


class RecordingEmailClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.fail_with: Exception | None = None

    def send_activation(
        self, *, to: str, full_name: str | None, login_url: str
    ) -> None:
        self.calls.append({"to": to, "full_name": full_name, "login_url": login_url})
        if self.fail_with is not None:
            raise self.fail_with


@pytest.fixture()
def recording_email_client() -> RecordingEmailClient:
    return RecordingEmailClient()


@pytest.fixture()
def client(database_url, db_session, recording_email_client):
    from fastapi.testclient import TestClient

    from app.deps import get_db
    from app.main import app
    from app.routers.auth import limiter
    from app.services.email_service import get_email_client

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_email_client] = lambda: recording_email_client
    limiter.reset()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    limiter.reset()


@pytest.fixture()
def make_user(db_session):
    """Factory: create_user(role='viewer', is_active=True, ...) -> User."""
    from app.models import User
    from app.services.auth_service import hash_password

    counter = {"n": 0}

    def _create(
        *,
        role: str = "viewer",
        is_active: bool = True,
        email: str | None = None,
        password: str = "password123",
        full_name: str | None = None,
    ):
        counter["n"] += 1
        from datetime import datetime

        user = User(
            email=email or f"user{counter['n']}-{role}@example.com",
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
            is_active=is_active,
            activated_at=datetime.now(tz=UTC) if is_active else None,
        )
        db_session.add(user)
        db_session.flush()
        return user, password

    return _create


@pytest.fixture()
def make_submission(db_session):
    """Build a Submission. If learner is None, also creates one under the rubric."""
    from app.models import Learner, Submission

    def _make(rubric, *, learner=None, status: str = "draft", created_by=None):
        if learner is None:
            learner = Learner(rubric_id=rubric.id, full_name="Auto Learner")
            db_session.add(learner)
            db_session.flush()
        sub = Submission(
            learner_id=learner.id,
            rubric_id=rubric.id,
            status=status,
            created_by=created_by,
        )
        db_session.add(sub)
        db_session.flush()
        return sub

    return _make


@pytest.fixture(scope="session", autouse=True)
def _cleanup_artifact_dir():
    yield
    shutil.rmtree(_TEST_ARTIFACT_DIR, ignore_errors=True)


@pytest.fixture()
def auth_headers(make_user):
    """Factory: auth_headers(role='viewer', is_active=True) -> {'Authorization': 'Bearer ...'}"""
    from app.services.auth_service import create_access_token

    def _headers(*, role: str = "viewer", is_active: bool = True):
        user, _ = make_user(role=role, is_active=is_active)
        token = create_access_token(user)
        return {"Authorization": f"Bearer {token}"}, user

    return _headers
