import pytest
from sqlalchemy import select

from app.config import Settings
from app.models import User
from app.services.auth_service import seed_superadmin


def _settings(**overrides) -> Settings:
    base = {
        "database_url": "postgresql+psycopg://x/y",
        "jwt_secret": "x",
        "superadmin_email": None,
        "superadmin_password": None,
    }
    base.update(overrides)
    return Settings(**base)


def _wipe_superadmins(db):
    for u in db.scalars(select(User).where(User.role == "superadmin")).all():
        db.delete(u)
    db.flush()


def test_seed_creates_superadmin_when_none_exists(db_session):
    _wipe_superadmins(db_session)
    cfg = _settings(superadmin_email="boot@admin.com", superadmin_password="bootpw")
    user = seed_superadmin(db_session, cfg)
    assert user is not None
    assert user.role == "superadmin"
    assert user.is_active is True
    assert user.email == "boot@admin.com"


def test_seed_is_idempotent_when_superadmin_exists(db_session):
    _wipe_superadmins(db_session)
    cfg = _settings(superadmin_email="first@admin.com", superadmin_password="pw1")
    seed_superadmin(db_session, cfg)
    cfg2 = _settings(superadmin_email="second@admin.com", superadmin_password="pw2")
    result = seed_superadmin(db_session, cfg2)
    assert result is None
    emails = {u.email for u in db_session.scalars(
        select(User).where(User.role == "superadmin")
    ).all()}
    assert emails == {"first@admin.com"}


def test_seed_raises_when_no_superadmin_and_env_vars_missing(db_session):
    _wipe_superadmins(db_session)
    cfg = _settings(superadmin_email=None, superadmin_password=None)
    with pytest.raises(RuntimeError, match="SUPERADMIN_EMAIL"):
        seed_superadmin(db_session, cfg)


def test_seed_no_op_when_admin_exists_even_if_env_vars_missing(db_session):
    _wipe_superadmins(db_session)
    cfg_seed = _settings(superadmin_email="kept@admin.com", superadmin_password="pw")
    seed_superadmin(db_session, cfg_seed)
    cfg_empty = _settings()
    assert seed_superadmin(db_session, cfg_empty) is None
