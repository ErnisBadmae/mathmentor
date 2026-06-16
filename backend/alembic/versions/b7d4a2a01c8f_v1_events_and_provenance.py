"""v1 events and provenance

Revision ID: b7d4a2a01c8f
Revises: a4fe3c90fb76
Create Date: 2026-06-16 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7d4a2a01c8f"
down_revision: Union[str, Sequence[str], None] = "a4fe3c90fb76"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("topic_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_evidence_topic_id_topics", "evidence", "topics", ["topic_id"], ["id"])
    op.create_index(op.f("ix_evidence_topic_id"), "evidence", ["topic_id"], unique=False)

    op.alter_column("error_events", "mission_id", existing_type=sa.UUID(), nullable=True)
    op.alter_column("error_events", "attempt_id", existing_type=sa.UUID(), nullable=True)
    op.alter_column("error_events", "evidence_id", existing_type=sa.UUID(), nullable=True)
    op.add_column("error_events", sa.Column("source_file", sa.String(length=500), nullable=True))
    op.add_column("error_events", sa.Column("source_sheet", sa.String(length=120), nullable=True))
    op.add_column("error_events", sa.Column("source_row", sa.Integer(), nullable=True))
    op.add_column("error_events", sa.Column("source_ref", sa.String(length=700), nullable=True))
    op.create_index(op.f("ix_error_events_source_ref"), "error_events", ["source_ref"], unique=True)

    op.alter_column("review_items", "source_evidence_id", existing_type=sa.UUID(), nullable=True)
    op.add_column("review_items", sa.Column("source_file", sa.String(length=500), nullable=True))
    op.add_column("review_items", sa.Column("source_sheet", sa.String(length=120), nullable=True))
    op.add_column("review_items", sa.Column("source_row", sa.Integer(), nullable=True))
    op.add_column("review_items", sa.Column("source_ref", sa.String(length=700), nullable=True))
    op.create_index(op.f("ix_review_items_source_ref"), "review_items", ["source_ref"], unique=True)

    op.create_table(
        "score_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("subject", sa.Enum("MATH_PROFILE", "INFORMATICS", name="subject", native_enum=False), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        sa.Column("source_sheet", sa.String(length=120), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("source_ref", sa.String(length=700), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_score_events_occurred_on"), "score_events", ["occurred_on"], unique=False)
    op.create_index(op.f("ix_score_events_source_ref"), "score_events", ["source_ref"], unique=True)
    op.create_index(op.f("ix_score_events_student_id"), "score_events", ["student_id"], unique=False)
    op.create_index(op.f("ix_score_events_subject"), "score_events", ["subject"], unique=False)

    op.create_table(
        "clean_sheet_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("tasks_total", sa.Integer(), nullable=False),
        sa.Column("clean_sheet_count", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        sa.Column("source_sheet", sa.String(length=120), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("source_ref", sa.String(length=700), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clean_sheet_events_occurred_on"), "clean_sheet_events", ["occurred_on"], unique=False)
    op.create_index(op.f("ix_clean_sheet_events_source_ref"), "clean_sheet_events", ["source_ref"], unique=True)
    op.create_index(op.f("ix_clean_sheet_events_student_id"), "clean_sheet_events", ["student_id"], unique=False)

    op.create_table(
        "study_log_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("subject", sa.Enum("MATH_PROFILE", "INFORMATICS", name="subject", native_enum=False), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("topic_title", sa.String(length=240), nullable=False),
        sa.Column("tasks_total", sa.Integer(), nullable=False),
        sa.Column("tasks_correct", sa.Integer(), nullable=False),
        sa.Column("percent_correct", sa.Float(), nullable=False),
        sa.Column("status_note", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("source_file", sa.String(length=500), nullable=True),
        sa.Column("source_sheet", sa.String(length=120), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("source_ref", sa.String(length=700), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_study_log_entries_occurred_on"), "study_log_entries", ["occurred_on"], unique=False)
    op.create_index(op.f("ix_study_log_entries_source_ref"), "study_log_entries", ["source_ref"], unique=True)
    op.create_index(op.f("ix_study_log_entries_student_id"), "study_log_entries", ["student_id"], unique=False)
    op.create_index(op.f("ix_study_log_entries_subject"), "study_log_entries", ["subject"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_study_log_entries_subject"), table_name="study_log_entries")
    op.drop_index(op.f("ix_study_log_entries_student_id"), table_name="study_log_entries")
    op.drop_index(op.f("ix_study_log_entries_source_ref"), table_name="study_log_entries")
    op.drop_index(op.f("ix_study_log_entries_occurred_on"), table_name="study_log_entries")
    op.drop_table("study_log_entries")

    op.drop_index(op.f("ix_clean_sheet_events_student_id"), table_name="clean_sheet_events")
    op.drop_index(op.f("ix_clean_sheet_events_source_ref"), table_name="clean_sheet_events")
    op.drop_index(op.f("ix_clean_sheet_events_occurred_on"), table_name="clean_sheet_events")
    op.drop_table("clean_sheet_events")

    op.drop_index(op.f("ix_score_events_subject"), table_name="score_events")
    op.drop_index(op.f("ix_score_events_student_id"), table_name="score_events")
    op.drop_index(op.f("ix_score_events_source_ref"), table_name="score_events")
    op.drop_index(op.f("ix_score_events_occurred_on"), table_name="score_events")
    op.drop_table("score_events")

    op.drop_index(op.f("ix_review_items_source_ref"), table_name="review_items")
    op.drop_column("review_items", "source_ref")
    op.drop_column("review_items", "source_row")
    op.drop_column("review_items", "source_sheet")
    op.drop_column("review_items", "source_file")
    op.alter_column("review_items", "source_evidence_id", existing_type=sa.UUID(), nullable=False)

    op.drop_index(op.f("ix_error_events_source_ref"), table_name="error_events")
    op.drop_column("error_events", "source_ref")
    op.drop_column("error_events", "source_row")
    op.drop_column("error_events", "source_sheet")
    op.drop_column("error_events", "source_file")
    op.alter_column("error_events", "evidence_id", existing_type=sa.UUID(), nullable=False)
    op.alter_column("error_events", "attempt_id", existing_type=sa.UUID(), nullable=False)
    op.alter_column("error_events", "mission_id", existing_type=sa.UUID(), nullable=False)

    op.drop_index(op.f("ix_evidence_topic_id"), table_name="evidence")
    op.drop_constraint("fk_evidence_topic_id_topics", "evidence", type_="foreignkey")
    op.drop_column("evidence", "topic_id")
