"""error category confirmation

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = 'e6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'error_events',
        sa.Column(
            'confirmed_category',
            sa.Enum(
                "ARITHMETIC",
                "SIGN_TRANSFER",
                "ODZ_LOGIC",
                "CONDITION_READING",
                "PROBABILITY_DOUBLE_COUNT",
                "UNKNOWN_METHOD",
                "ALGORITHM_LOGIC",
                "CODE_SYNTAX",
                "CODE_ALGORITHM",
                "TIME_MANAGEMENT",
                "NONE",
                "OTHER",
                name="errorcategory",
                native_enum=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        'error_events',
        sa.Column('category_confirmed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'error_events',
        sa.Column('category_confirmation_source', sa.String(length=80), nullable=True),
    )
    op.create_index(
        op.f('ix_error_events_confirmed_category'),
        'error_events',
        ['confirmed_category'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_error_events_confirmed_category'), table_name='error_events')
    op.drop_column('error_events', 'category_confirmation_source')
    op.drop_column('error_events', 'category_confirmed_at')
    op.drop_column('error_events', 'confirmed_category')
