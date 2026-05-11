import logging
import mimetypes
from pathlib import PurePath
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_db, require_admin_or_evaluator
from app.models import Submission, SubmissionArtifact, User
from app.routers.submissions import _submission_in_scope
from app.schemas.artifact import ArtifactLinksCreate, ArtifactOut, ArtifactTextCreate
from app.services.artifact_storage import (
    FileTooLargeError,
    LocalArtifactStorage,
    get_artifact_storage,
)
from app.services.artifact_token import decode_artifact_token

logger = logging.getLogger(__name__)

nested_router = APIRouter(
    prefix="/submissions/{submission_id}/artifacts", tags=["artifacts"]
)
flat_router = APIRouter(prefix="/artifacts", tags=["artifacts"])

# File uploads are limited to screenshots; videos must come in as Loom or
# Google Drive links since that is what n8n consumes.
ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    "screenshot": {".png", ".jpg", ".jpeg"},
}


def _safe_filename(filename: str) -> str:
    """Strip directory traversal and reject empty/dotted names. We trust the
    caller for the descriptive part of the name but never the path."""
    base = PurePath(filename).name
    if not base or base in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename"
        )
    return base


def _ensure_not_processing(submission: Submission) -> None:
    """Artifacts can be edited any time except while n8n is mid-run. Mutating
    artifacts on complete or failed is allowed so the evaluator can fix things
    up and re-evaluate."""
    if submission.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot modify artifacts while the submission is processing",
        )


def _get_writable_submission(
    submission_id: UUID, user: User, db: Session
) -> Submission:
    submission = _submission_in_scope(submission_id, user, db)
    _ensure_not_processing(submission)
    return submission


@nested_router.post(
    "", response_model=list[ArtifactOut], status_code=status.HTTP_201_CREATED
)
def upload_files(
    submission_id: UUID,
    type: str = Form(...),
    files: list[UploadFile] = File(...),
    user: User = Depends(require_admin_or_evaluator),
    db: Session = Depends(get_db),
    storage: LocalArtifactStorage = Depends(get_artifact_storage),
) -> list[SubmissionArtifact]:
    if type not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"type must be one of {sorted(ALLOWED_EXTENSIONS)}",
        )
    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="No files provided"
        )

    submission = _get_writable_submission(submission_id, user, db)
    allowed_exts = ALLOWED_EXTENSIONS[type]

    existing_total = db.scalar(
        select(func.coalesce(func.sum(SubmissionArtifact.size_bytes), 0)).where(
            SubmissionArtifact.submission_id == submission.id
        )
    ) or 0

    created: list[SubmissionArtifact] = []
    for upload in files:
        if not upload.filename:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="One of the uploaded files has no name",
            )
        filename = _safe_filename(upload.filename)
        ext = PurePath(filename).suffix.lower()
        if ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Extension {ext or '(none)'} not allowed for type {type}",
            )
        if storage.exists(submission.id, filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An artifact named '{filename}' already exists in this submission",
            )

        try:
            written = storage.write_streamed(
                submission.id, filename, upload, settings.max_file_bytes
            )
        except FileTooLargeError as exc:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)
            ) from exc

        if existing_total + written > settings.max_submission_bytes:
            storage.delete_file(submission.id, filename)
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=(
                    f"Adding this file would exceed the per-submission limit of "
                    f"{settings.max_submission_bytes} bytes"
                ),
            )
        existing_total += written

        artifact = SubmissionArtifact(
            submission_id=submission.id,
            type=type,
            filename=filename,
            storage_path=str(storage.file_path(submission.id, filename)),
            size_bytes=written,
        )
        db.add(artifact)
        db.flush()
        created.append(artifact)

    db.commit()
    for a in created:
        db.refresh(a)
    return created


@nested_router.post(
    "/links", response_model=list[ArtifactOut], status_code=status.HTTP_201_CREATED
)
def add_links(
    submission_id: UUID,
    body: ArtifactLinksCreate,
    user: User = Depends(require_admin_or_evaluator),
    db: Session = Depends(get_db),
) -> list[SubmissionArtifact]:
    submission = _get_writable_submission(submission_id, user, db)
    created: list[SubmissionArtifact] = []
    for link in body.links:
        artifact = SubmissionArtifact(
            submission_id=submission.id,
            type=link.type,
            external_url=str(link.url),
        )
        db.add(artifact)
        db.flush()
        created.append(artifact)
    db.commit()
    for a in created:
        db.refresh(a)
    return created


@nested_router.post(
    "/text", response_model=ArtifactOut, status_code=status.HTTP_201_CREATED
)
def add_text(
    submission_id: UUID,
    body: ArtifactTextCreate,
    user: User = Depends(require_admin_or_evaluator),
    db: Session = Depends(get_db),
) -> SubmissionArtifact:
    submission = _get_writable_submission(submission_id, user, db)
    artifact = SubmissionArtifact(
        submission_id=submission.id,
        type="text",
        text_value=body.value,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


@nested_router.delete(
    "/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_artifact(
    submission_id: UUID,
    artifact_id: UUID,
    user: User = Depends(require_admin_or_evaluator),
    db: Session = Depends(get_db),
    storage: LocalArtifactStorage = Depends(get_artifact_storage),
) -> None:
    submission = _get_writable_submission(submission_id, user, db)
    artifact = db.get(SubmissionArtifact, artifact_id)
    if artifact is None or artifact.submission_id != submission.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    filename = artifact.filename
    is_file = artifact.type in ALLOWED_EXTENSIONS  # currently just screenshot
    db.delete(artifact)
    db.commit()
    if is_file and filename:
        storage.delete_file(submission.id, filename)


@flat_router.get("/{token}")
def download_artifact(
    token: str,
    db: Session = Depends(get_db),
    storage: LocalArtifactStorage = Depends(get_artifact_storage),
) -> FileResponse:
    """Signed-URL artifact download. The JWT in the path IS the auth - no user
    session required. n8n calls this with a token issued by /submissions/{id}/evaluate."""
    try:
        submission_id, filename = decode_artifact_token(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        ) from exc

    artifact = db.scalar(
        select(SubmissionArtifact).where(
            SubmissionArtifact.submission_id == submission_id,
            SubmissionArtifact.filename == filename,
            SubmissionArtifact.type == "screenshot",
        )
    )
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    path = storage.file_path(submission_id, filename)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact file missing")

    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(
        path=path,
        media_type=media_type or "application/octet-stream",
        filename=filename,
    )
