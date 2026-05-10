import logging
import shutil
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from fastapi import UploadFile

from app.config import settings

logger = logging.getLogger(__name__)

CHUNK_SIZE = 64 * 1024


class FileTooLargeError(Exception):
    """Raised when a single file exceeds the configured per-file byte limit."""


class LocalArtifactStorage:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _submission_dir(self, submission_id: UUID) -> Path:
        return self.root / str(submission_id)

    def file_path(self, submission_id: UUID, filename: str) -> Path:
        return self._submission_dir(submission_id) / filename

    def exists(self, submission_id: UUID, filename: str) -> bool:
        return self.file_path(submission_id, filename).is_file()

    def write_streamed(
        self,
        submission_id: UUID,
        filename: str,
        upload: UploadFile,
        max_bytes: int,
    ) -> int:
        """Stream the upload to disk in 64KB chunks; abort + clean up if it
        exceeds max_bytes. Returns the bytes written on success."""
        sub_dir = self._submission_dir(submission_id)
        sub_dir.mkdir(parents=True, exist_ok=True)
        dest = sub_dir / filename
        written = 0
        try:
            with dest.open("wb") as out:
                while True:
                    chunk = upload.file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_bytes:
                        out.close()
                        dest.unlink(missing_ok=True)
                        raise FileTooLargeError(
                            f"File '{filename}' exceeds the {max_bytes}-byte limit"
                        )
                    out.write(chunk)
        except FileTooLargeError:
            raise
        except Exception:
            dest.unlink(missing_ok=True)
            raise
        return written

    def open_for_read(self, submission_id: UUID, filename: str) -> BinaryIO:
        return self.file_path(submission_id, filename).open("rb")

    def delete_file(self, submission_id: UUID, filename: str) -> None:
        path = self.file_path(submission_id, filename)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning(
                "artifact disk delete failed for submission_id=%s filename=%s: %s",
                submission_id,
                filename,
                exc,
            )

    def delete_submission_dir(self, submission_id: UUID) -> None:
        path = self._submission_dir(submission_id)
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)


@lru_cache(maxsize=1)
def get_artifact_storage() -> LocalArtifactStorage:
    return LocalArtifactStorage(settings.artifact_dir)
