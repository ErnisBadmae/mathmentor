"""topic program phase

Revision ID: d1a2b3c4e5f6
Revises: c9f1e2a4b8d0
Create Date: 2026-06-17 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d1a2b3c4e5f6"
down_revision: str | Sequence[str] | None = "c9f1e2a4b8d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("topics", sa.Column("phase", sa.String(length=40), nullable=True))
    op.add_column("topics", sa.Column("program_order", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_topics_phase"), "topics", ["phase"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_topics_phase"), table_name="topics")
    op.drop_column("topics", "program_order")
    op.drop_column("topics", "phase")
