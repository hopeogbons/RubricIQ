"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-10

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('full_name', sa.String(), nullable=True),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('activated_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("role in ('superadmin','admin','evaluator','viewer')", name='users_role_check'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('rubrics',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('unique_name', sa.String(), nullable=False),
    sa.Column('display_name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('google_sheet_id', sa.String(), nullable=True),
    sa.Column('google_drive_folder_path', sa.String(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('unique_name')
    )
    op.create_table('learners',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('rubric_id', sa.UUID(), nullable=False),
    sa.Column('full_name', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('cohort', sa.String(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['rubric_id'], ['rubrics.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('rubric_id', 'email', name='learners_rubric_id_email_key')
    )
    op.create_index('ix_learners_rubric_id', 'learners', ['rubric_id'], unique=False)
    op.create_table('submissions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('learner_id', sa.UUID(), nullable=False),
    sa.Column('rubric_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(), server_default='draft', nullable=False),
    sa.Column('triggered_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('error_message', sa.String(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status in ('draft','processing','complete','failed')", name='submissions_status_check'),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['learner_id'], ['learners.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rubric_id'], ['rubrics.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_submissions_learner_id', 'submissions', ['learner_id'], unique=False)
    op.create_index('ix_submissions_rubric_id_status', 'submissions', ['rubric_id', 'status'], unique=False)
    op.create_table('evaluations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('submission_id', sa.UUID(), nullable=False),
    sa.Column('total_score', sa.Numeric(), nullable=True),
    sa.Column('max_total', sa.Numeric(), nullable=True),
    sa.Column('raw_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('evaluated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('submission_id')
    )
    op.create_table('submission_artifacts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('submission_id', sa.UUID(), nullable=False),
    sa.Column('type', sa.String(), nullable=False),
    sa.Column('storage_path', sa.String(), nullable=True),
    sa.Column('external_url', sa.String(), nullable=True),
    sa.Column('filename', sa.String(), nullable=True),
    sa.Column('size_bytes', sa.BigInteger(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("type in ('video_file','screenshot','video_link','github_link')", name='submission_artifacts_type_check'),
    sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('evaluation_scores',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('evaluation_id', sa.UUID(), nullable=False),
    sa.Column('criterion', sa.String(), nullable=False),
    sa.Column('score', sa.Numeric(), nullable=False),
    sa.Column('max_score', sa.Numeric(), nullable=False),
    sa.Column('explanation', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evaluation_scores_evaluation_id', 'evaluation_scores', ['evaluation_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_evaluation_scores_evaluation_id', table_name='evaluation_scores')
    op.drop_table('evaluation_scores')
    op.drop_table('submission_artifacts')
    op.drop_table('evaluations')
    op.drop_index('ix_submissions_rubric_id_status', table_name='submissions')
    op.drop_index('ix_submissions_learner_id', table_name='submissions')
    op.drop_table('submissions')
    op.drop_index('ix_learners_rubric_id', table_name='learners')
    op.drop_table('learners')
    op.drop_table('rubrics')
    op.drop_table('users')
