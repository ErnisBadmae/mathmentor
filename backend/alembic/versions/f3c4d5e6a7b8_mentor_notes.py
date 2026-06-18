"""mentor notes

Revision ID: f3c4d5e6a7b8
Revises: e2b3c4d5f6a7
Create Date: 2026-06-18 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f3c4d5e6a7b8"
down_revision: str | Sequence[str] | None = "e2b3c4d5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mentor_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("topic_id", sa.UUID(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"]),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mentor_notes_student_id"), "mentor_notes", ["student_id"], unique=False
    )
    op.create_index(op.f("ix_mentor_notes_topic_id"), "mentor_notes", ["topic_id"], unique=False)
    op.create_index(
        op.f("ix_mentor_notes_created_at"), "mentor_notes", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_mentor_notes_created_at"), table_name="mentor_notes")
    op.drop_index(op.f("ix_mentor_notes_topic_id"), table_name="mentor_notes")
    op.drop_index(op.f("ix_mentor_notes_student_id"), table_name="mentor_notes")
    op.drop_table("mentor_notes")
