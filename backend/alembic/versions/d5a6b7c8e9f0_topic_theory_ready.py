"""topic theory_ready_at

Revision ID: d5a6b7c8e9f0
Revises: c0d1e2f3a4b5
Create Date: 2026-07-07 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d5a6b7c8e9f0"
down_revision: str | Sequence[str] | None = "c0d1e2f3a4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "topics", sa.Column("theory_ready_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("topics", "theory_ready_at")
