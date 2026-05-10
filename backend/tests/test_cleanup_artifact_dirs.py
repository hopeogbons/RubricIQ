import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.services.artifact_storage import LocalArtifactStorage
from app.tasks.cleanup import cleanup_old_artifact_dirs


@pytest.fixture()
def storage(tmp_path: Path) -> LocalArtifactStorage:
    return LocalArtifactStorage(tmp_path)


def _make_dir(root: Path, name: str, *, age_seconds: int) -> Path:
    target = root / name
    target.mkdir(parents=True, exist_ok=True)
    (target / "shot.png").write_bytes(b"PNG")
    age = (datetime.now() - timedelta(seconds=age_seconds)).timestamp()
    os.utime(target, (age, age))
    return target


def test_old_dir_is_removed_young_dir_is_kept(storage):
    old = _make_dir(storage.root, "old", age_seconds=2 * 60 * 60)  # 2 hours old
    young = _make_dir(storage.root, "young", age_seconds=10)
    result = cleanup_old_artifact_dirs(storage, ttl_hours=1)
    assert result["deleted"] == 1
    assert not old.exists()
    assert young.exists()


def test_now_parameter_overrides_clock(storage):
    target = _make_dir(storage.root, "x", age_seconds=10)
    far_future = datetime.now(tz=UTC) + timedelta(days=365)
    result = cleanup_old_artifact_dirs(storage, ttl_hours=1, now=far_future)
    assert result["deleted"] == 1
    assert not target.exists()


def test_missing_root_is_tolerated(tmp_path: Path):
    storage = LocalArtifactStorage(tmp_path / "does-not-exist")
    result = cleanup_old_artifact_dirs(storage, ttl_hours=1)
    assert result == {"deleted": 0}


def test_files_at_root_are_ignored(storage):
    (storage.root).mkdir(parents=True, exist_ok=True)
    stray = storage.root / "stray.png"
    stray.write_bytes(b"x")
    age = (datetime.now() - timedelta(days=1)).timestamp()
    os.utime(stray, (age, age))
    result = cleanup_old_artifact_dirs(storage, ttl_hours=1)
    assert result["deleted"] == 0
    assert stray.exists()
