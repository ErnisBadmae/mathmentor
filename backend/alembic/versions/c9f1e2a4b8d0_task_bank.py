"""task bank

Revision ID: c9f1e2a4b8d0
Revises: b7d4a2a01c8f
Create Date: 2026-06-17 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c9f1e2a4b8d0"
down_revision: str | Sequence[str] | None = "b7d4a2a01c8f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "subject",
            sa.Enum("MATH_PROFILE", "INFORMATICS", name="subject", native_enum=False),
            nullable=False,
        ),
        sa.Column("topic_id", sa.UUID(), nullable=True),
        sa.Column("task_number", sa.String(length=32), nullable=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=False),
        sa.Column("solution", sa.Text(), nullable=True),
        sa.Column(
            "error_category",
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
        sa.Column(
            "status",
            sa.Enum("DRAFT", "APPROVED", name="taskstatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("model_id", sa.String(length=160), nullable=True),
        sa.Column("prompt_version", sa.String(length=80), nullable=True),
        sa.Column("source_ref", sa.String(length=700), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tasks_error_category"), "tasks", ["error_category"], unique=False)
    op.create_index(op.f("ix_tasks_source_ref"), "tasks", ["source_ref"], unique=True)
    op.create_index(op.f("ix_tasks_status"), "tasks", ["status"], unique=False)
    op.create_index(op.f("ix_tasks_subject"), "tasks", ["subject"], unique=False)
    op.create_index(op.f("ix_tasks_topic_id"), "tasks", ["topic_id"], unique=False)

    op.add_column("missions", sa.Column("task_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_missions_task_id_tasks", "missions", "tasks", ["task_id"], ["id"])
    op.create_index(op.f("ix_missions_task_id"), "missions", ["task_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_missions_task_id"), table_name="missions")
    op.drop_constraint("fk_missions_task_id_tasks", "missions", type_="foreignkey")
    op.drop_column("missions", "task_id")

    op.drop_index(op.f("ix_tasks_topic_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_subject"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_status"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_source_ref"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_error_category"), table_name="tasks")
    op.drop_table("tasks")
