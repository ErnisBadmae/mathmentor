"""task source_url

Revision ID: e2b3c4d5f6a7
Revises: d1a2b3c4e5f6
Create Date: 2026-06-17 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e2b3c4d5f6a7"
down_revision: str | Sequence[str] | None = "d1a2b3c4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("source_url", sa.String(length=700), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "source_url")
