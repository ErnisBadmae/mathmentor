"""Persist timed CISIA practice independently of EGE evidence."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "b0c1d2e3f4a5"
down_revision = "a9b0c1d2e3f4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "timed_blocks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("student_id", sa.Uuid(), sa.ForeignKey("student_profiles.id"), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        *[
            sa.Column(name, JSONB(), nullable=False)
            for name in ("task_ids", "familiar_task_ids", "answer_key", "answers")
        ],
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("finish_reason", sa.String(20)),
        sa.Column("correct", sa.Integer()),
        sa.Column("total", sa.Integer(), nullable=False),
    )
    op.create_index(
        "uq_timed_blocks_open_student",
        "timed_blocks",
        ["student_id"],
        unique=True,
        postgresql_where=sa.text("finished_at IS NULL"),
    )


def downgrade():
    op.drop_table("timed_blocks")
