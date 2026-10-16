"""Row locks serialize block changes; all deadline decisions use the database clock."""

from datetime import UTC

from sqlalchemy import func, select, update

from app.infrastructure.models import MissionORM, StudentProfileORM, TimedBlockORM


class TimedBlockSqlRepository:
    def __init__(self, session):
        self.session = session

    def now(self):
        # SQLite is only the unit-test adapter. Production always uses clock_timestamp.
        value = self.session.scalar(
            select(
                func.clock_timestamp()
                if self.session.bind.dialect.name == "postgresql"
                else func.current_timestamp()
            )
        )
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value

    def lock_student(self, student_id):
        student = self.session.scalar(
            select(StudentProfileORM).where(StudentProfileORM.id == student_id).with_for_update()
        )
        if student is None:
            raise LookupError("Student not found")

    def active(self, student_id):
        return self.session.scalar(
            select(TimedBlockORM)
            .where(TimedBlockORM.student_id == student_id, TimedBlockORM.finished_at.is_(None))
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def get(self, student_id, block_id):
        block = self.session.scalar(
            select(TimedBlockORM)
            .where(TimedBlockORM.student_id == student_id, TimedBlockORM.id == block_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if block is None:
            raise LookupError("Timed block not found")
        return block

    def latest(self, student_id):
        return self.session.scalar(
            select(TimedBlockORM)
            .where(TimedBlockORM.student_id == student_id)
            .order_by(TimedBlockORM.started_at.desc())
            .limit(1)
        )

    def familiar_ids(self, student_id):
        # Old dialogue did not persist views: assignment is conservative exposure.
        ids = {
            str(value)
            for value in self.session.scalars(
                select(MissionORM.task_id).where(
                    MissionORM.student_id == student_id, MissionORM.task_id.is_not(None)
                )
            )
        }
        for task_ids in self.session.scalars(
            select(TimedBlockORM.task_ids).where(TimedBlockORM.student_id == student_id)
        ):
            ids.update(task_ids)
        return ids

    def create(self, values):
        block = TimedBlockORM(**values)
        self.session.add(block)
        self.session.flush()
        return block

    def save_answer(self, block, task_id, answer):
        clock = (
            func.clock_timestamp()
            if self.session.bind.dialect.name == "postgresql"
            else func.current_timestamp()
        )
        result = self.session.execute(
            update(TimedBlockORM)
            .where(
                TimedBlockORM.id == block.id,
                TimedBlockORM.finished_at.is_(None),
                clock < TimedBlockORM.deadline_at,
            )
            .values(answers={**block.answers, task_id: answer})
            .execution_options(synchronize_session=False)
        )
        self.session.refresh(block)
        return bool(result.rowcount)

    def finish(self, block, values):
        result = self.session.execute(
            update(TimedBlockORM)
            .where(TimedBlockORM.id == block.id, TimedBlockORM.finished_at.is_(None))
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        self.session.refresh(block)
        return bool(result.rowcount)
