"""slice details_json

Revision ID: b8e4f1a2c3d9
Revises: a1b2c3d4e5f7
Create Date: 2026-06-23 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b8e4f1a2c3d9"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("study_log_entries", sa.Column("details_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("study_log_entries", "details_json")
