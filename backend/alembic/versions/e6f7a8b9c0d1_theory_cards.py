"""theory cards

Revision ID: e6f7a8b9c0d1
Revises: d5a6b7c8e9f0
Create Date: 2026-07-08 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | Sequence[str] | None = "d5a6b7c8e9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "theory_cards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("body_md", sa.Text(), nullable=False),
        sa.Column("visual_kind", sa.String(length=80), nullable=False),
        sa.Column("visual_mode", sa.String(length=20), nullable=False),
        sa.Column("visual_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source_ref", sa.String(length=700), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_theory_cards_source_ref"), "theory_cards", ["source_ref"], unique=True)
    op.create_index(op.f("ix_theory_cards_status"), "theory_cards", ["status"], unique=False)
    op.create_index(op.f("ix_theory_cards_topic_id"), "theory_cards", ["topic_id"], unique=False)
    op.create_index(
        op.f("ix_theory_cards_visual_mode"), "theory_cards", ["visual_mode"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_theory_cards_visual_mode"), table_name="theory_cards")
    op.drop_index(op.f("ix_theory_cards_topic_id"), table_name="theory_cards")
    op.drop_index(op.f("ix_theory_cards_status"), table_name="theory_cards")
    op.drop_index(op.f("ix_theory_cards_source_ref"), table_name="theory_cards")
    op.drop_table("theory_cards")
