"""n8n contract alignment: one submission per learner, new artifact vocab, text artifacts

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


NEW_TYPES = ("loom", "gdrive_video", "github", "screenshot", "text")


def upgrade() -> None:
    # One submission per learner. The existing non-unique index is replaced
    # with a unique one; using IF EXISTS keeps the migration safe to re-run.
    op.drop_index("ix_submissions_learner_id", table_name="submissions")
    op.create_index(
        "ix_submissions_learner_id",
        "submissions",
        ["learner_id"],
        unique=True,
    )

    # text artifacts carry a free-form string instead of a URL or file.
    op.add_column(
        "submission_artifacts",
        sa.Column("text_value", sa.Text(), nullable=True),
    )

    # Swap the artifact type vocabulary. video_file is dropped (n8n only takes
    # videos as Loom or Google Drive links); video_link/github_link are
    # renamed to loom/github; new gdrive_video and text types are added.
    op.drop_constraint(
        "submission_artifacts_type_check",
        "submission_artifacts",
        type_="check",
    )
    op.create_check_constraint(
        "submission_artifacts_type_check",
        "submission_artifacts",
        f"type in {NEW_TYPES}",
    )


def downgrade() -> None:
    op.drop_constraint(
        "submission_artifacts_type_check",
        "submission_artifacts",
        type_="check",
    )
    op.create_check_constraint(
        "submission_artifacts_type_check",
        "submission_artifacts",
        "type in ('video_file','screenshot','video_link','github_link')",
    )

    op.drop_column("submission_artifacts", "text_value")

    op.drop_index("ix_submissions_learner_id", table_name="submissions")
    op.create_index(
        "ix_submissions_learner_id",
        "submissions",
        ["learner_id"],
        unique=False,
    )
