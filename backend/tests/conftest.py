import os
import shutil
from collections.abc import Generator

import pytest
from pytest_postgresql import factories
from pytest_postgresql.janitor import DatabaseJanitor

PG_BIN = "/usr/local/opt/postgresql@18/bin"
if os.path.isdir(PG_BIN):
    os.environ["PATH"] = f"{PG_BIN}:{os.environ.get('PATH', '')}"

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

    from alembic.config import Config

    from alembic import command

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")

    yield url

    janitor.drop()


@pytest.fixture()
def db_session(database_url):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(database_url, future=True)
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
        engine.dispose()


@pytest.fixture()
def client(database_url):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
