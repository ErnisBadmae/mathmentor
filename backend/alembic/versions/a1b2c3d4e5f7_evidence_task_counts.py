"""evidence task counts

Revision ID: a1b2c3d4e5f7
Revises: f3c4d5e6a7b8
Create Date: 2026-06-22 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f7"
down_revision = "f3c4d5e6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("tasks_total", sa.Integer(), nullable=True))
    op.add_column("evidence", sa.Column("tasks_correct", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("evidence", "tasks_correct")
    op.drop_column("evidence", "tasks_total")
