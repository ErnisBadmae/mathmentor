"""mentor_note delivered_at

Revision ID: c0d1e2f3a4b5
Revises: b8e4f1a2c3d9
Create Date: 2026-06-24 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c0d1e2f3a4b5"
down_revision: str | Sequence[str] | None = "b8e4f1a2c3d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mentor_notes", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("mentor_notes", "delivered_at")
