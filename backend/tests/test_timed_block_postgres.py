"""Real row-lock/deadline tests in an isolated schema; explicit URL required."""

import importlib.util
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from app.application.use_cases import LearningService, RuleBasedReviewer
from app.domain.enums import Role, Subject
from app.infrastructure.db import Base
from app.infrastructure.models import StudentProfileORM, TimedBlockORM, UserORM
from app.infrastructure.repositories import SqlAlchemyUnitOfWork
from scripts.seed import DEMO_STUDENT_ID as STUDENT


def service(session):
    return LearningService(SqlAlchemyUnitOfWork(session), RuleBasedReviewer())


@pytest.fixture
def pg_factory():
    url = os.environ.get("TIMED_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TIMED_TEST_DATABASE_URL for PostgreSQL lock tests")
    root = create_engine(url)
    schema = "timed_test_" + uuid4().hex
    with root.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        # Build existing tables, then exercise the actual new Alembic migration.
        Base.metadata.create_all(
            engine, tables=[t for t in Base.metadata.sorted_tables if t.name != "timed_blocks"]
        )
        path = Path(__file__).parents[1] / "alembic/versions/b0c1d2e3f4a5_timed_blocks.py"
        spec = importlib.util.spec_from_file_location("timed_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()
        factory = sessionmaker(engine, expire_on_commit=False)
        with factory() as session:
            user_id = uuid4()
            session.add(
                UserORM(
                    id=user_id,
                    display_name="Synthetic",
                    role=Role.STUDENT,
                    created_at=datetime.now(UTC),
                )
            )
            session.flush()
            session.add(
                StudentProfileORM(
                    id=STUDENT, user_id=user_id, exam_year=2027, display_name="Synthetic"
                )
            )
            session.commit()
            svc = service(session)
            bundle = json.loads((Path(__file__).parents[1] / "data/cisia/math.json").read_text())
            for q in bundle["questions"]:
                task = svc.add_task(
                    {
                        "subject": Subject.MATH_PROFILE,
                        "source": "cisia_sample",
                        "source_ref": q["source_ref"],
                        "statement": "Synthetic",
                        "expected_answer": q["expected_answer"],
                    }
                )
                svc.approve_task(task.id)
        yield factory
    finally:
        engine.dispose()
        with root.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def test_parallel_start_and_finish_are_idempotent(pg_factory):
    barrier = threading.Barrier(2)

    def start():
        with pg_factory() as session:
            barrier.wait(timeout=5)
            return service(session).start_timed_block(STUDENT)

    with ThreadPoolExecutor(2) as executor:
        blocks = list(executor.map(lambda _: start(), range(2)))
    assert blocks[0]["id"] == blocks[1]["id"]
    barrier.reset()

    def finish():
        with pg_factory() as session:
            barrier.wait(timeout=5)
            return service(session).finish_timed_block(STUDENT, blocks[0]["id"])

    with ThreadPoolExecutor(2) as executor:
        results = list(executor.map(lambda _: finish(), range(2)))
    assert sum(result["newly_finished"] for result in results) == 1
    with pg_factory() as session:
        assert session.scalar(select(func.count()).select_from(TimedBlockORM)) == 1


def test_waiting_for_lock_does_not_extend_deadline(pg_factory):
    with pg_factory() as session:
        block = service(session).start_timed_block(STUDENT)
    ready = threading.Event()
    # Holder exits before executor joins, also when readiness assertions fail.
    with ThreadPoolExecutor(1) as executor, pg_factory() as holder:
        holder.execute(
            select(StudentProfileORM).where(StudentProfileORM.id == STUDENT).with_for_update()
        )
        row = holder.get(TimedBlockORM, block["id"])
        row.deadline_at = holder.scalar(select(func.clock_timestamp())) + timedelta(seconds=0.4)
        holder.flush()

        def answer():
            with pg_factory() as session:
                # Freeze PostgreSQL transaction_timestamp before the blocked request.
                session.execute(select(func.now()))
                ready.set()
                return service(session).answer_timed_block(STUDENT, block["id"], 0, "A")

        future = executor.submit(answer)
        assert ready.wait(timeout=15)
        holder.execute(text("SELECT pg_sleep(0.7)"))
        holder.commit()
        result = future.result(timeout=15)
    assert result["finish_reason"] == "deadline" and result["skipped"] == 5


def test_answer_and_finish_use_one_locked_snapshot(pg_factory):
    with pg_factory() as session:
        block = service(session).start_timed_block(STUDENT)
        row = session.get(TimedBlockORM, block["id"])
        expected = row.answer_key[row.task_ids[0]]
    barrier = threading.Barrier(2)

    def request(finish):
        with pg_factory() as session:
            barrier.wait(timeout=5)
            svc = service(session)
            return (
                svc.finish_timed_block(STUDENT, block["id"])
                if finish
                else svc.answer_timed_block(STUDENT, block["id"], 0, expected)
            )

    with ThreadPoolExecutor(2) as executor:
        list(executor.map(request, [False, True]))
    with pg_factory() as session:
        row = session.get(TimedBlockORM, block["id"])
        assert row.finished_at is not None
        assert row.correct == sum(
            row.answers.get(key) == value for key, value in row.answer_key.items()
        )
        before = row.answers.copy()
        assert service(session).answer_timed_block(STUDENT, row.id, 1, "B")["finished"]
        assert row.answers == before
