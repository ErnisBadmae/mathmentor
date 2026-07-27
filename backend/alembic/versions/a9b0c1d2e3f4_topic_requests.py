"""topic requests (demand signal)

Revision ID: a9b0c1d2e3f4
Revises: f7a8b9c0d1e2
Create Date: 2026-07-27 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a9b0c1d2e3f4"
down_revision: str | Sequence[str] | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "topic_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"]),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_topic_requests_student_id"), "topic_requests", ["student_id"], unique=False
    )
    op.create_index(
        op.f("ix_topic_requests_topic_id"), "topic_requests", ["topic_id"], unique=False
    )
    op.create_index(
        op.f("ix_topic_requests_outcome"), "topic_requests", ["outcome"], unique=False
    )
    op.create_index(
        op.f("ix_topic_requests_created_at"), "topic_requests", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_topic_requests_created_at"), table_name="topic_requests")
    op.drop_index(op.f("ix_topic_requests_outcome"), table_name="topic_requests")
    op.drop_index(op.f("ix_topic_requests_topic_id"), table_name="topic_requests")
    op.drop_index(op.f("ix_topic_requests_student_id"), table_name="topic_requests")
    op.drop_table("topic_requests")
