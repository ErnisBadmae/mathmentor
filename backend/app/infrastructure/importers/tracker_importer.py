from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import ErrorCategory, ReviewStatus, Subject
from app.infrastructure.importers.xlsx_reader import SheetPreview, read_xlsx
from app.infrastructure.models import (
    CleanSheetEventORM,
    ErrorEventORM,
    ReviewItemORM,
    ScoreEventORM,
    StudentProfileORM,
    StudyLogEntryORM,
    SubjectTrackORM,
    TopicORM,
)


DEMO_STUDENT_ID = UUID("00000000-0000-0000-0000-000000000000")


@dataclass(frozen=True)
class ImportSummary:
    dashboard_tracks: int = 0
    study_log_entries: int = 0
    error_events: int = 0
    clean_sheet_events: int = 0
    review_items: int = 0
    score_events: int = 0


def default_tracker_path() -> Path:
    return Path.home() / "Desktop" / "ЕГЭ" / "контроль" / "трекер_ЕГЭ-финал.xlsx"


def _cell(row: list[str], index: int) -> str:
    return row[index].strip() if index < len(row) and row[index] is not None else ""


def _number(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def _int(value: str) -> int | None:
    number = _number(value)
    return None if number is None else int(round(number))


def _date(value: str) -> date | None:
    if not value:
        return None
    number = _number(value)
    if number is not None:
        return date(1899, 12, 30) + timedelta(days=int(number))
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    if value.count(".") == 1:
        try:
            parsed = datetime.strptime(f"{value}.2026", "%d.%m.%Y").date()
            return parsed
        except ValueError:
            return None
    return None


def _datetime(value: str) -> datetime:
    parsed = _date(value) or date.today()
    return datetime.combine(parsed, time.min, tzinfo=UTC)


def _subject(value: str) -> Subject | None:
    normalized = value.lower()
    if "информ" in normalized:
        return Subject.INFORMATICS
    if "матем" in normalized or "проф" in normalized:
        return Subject.MATH_PROFILE
    return None


def _category(category: str, task_type: str, detail: str) -> ErrorCategory:
    text = " ".join([category, task_type, detail]).lower()
    if "ариф" in text or "перенос" in text or "знак" in text:
        return ErrorCategory.ARITHMETIC
    if "двойн" in text or "вероят" in text and "логик" in text:
        return ErrorCategory.PROBABILITY_DOUBLE_COUNT
    if "одз" in text:
        return ErrorCategory.ODZ_LOGIC
    if "услов" in text or "прочитал" in text:
        return ErrorCategory.CONDITION_READING
    if "синтак" in text:
        return ErrorCategory.CODE_SYNTAX
    if "код" in text:
        return ErrorCategory.CODE_ALGORITHM
    if "алгоритм" in text or "логик" in text:
        return ErrorCategory.ALGORITHM_LOGIC
    return ErrorCategory.OTHER


def _source_ref(path: Path, sheet_name: str, row_number: int, suffix: str = "") -> str:
    base = f"{path.resolve()}::{sheet_name}::{row_number}"
    return f"{base}::{suffix}" if suffix else base


def _sheet(sheets: list[SheetPreview], name: str) -> SheetPreview | None:
    return next((sheet for sheet in sheets if sheet.name == name), None)


def _has_source(session: Session, model: type, source_ref: str) -> bool:
    return session.scalar(select(model).where(model.source_ref == source_ref)) is not None


def _topic(session: Session, subject: Subject, title: str) -> TopicORM:
    existing = session.scalar(select(TopicORM).where(TopicORM.subject == subject).where(TopicORM.title == title))
    if existing is not None:
        return existing
    topic = TopicORM(id=uuid4(), subject=subject, title=title, spec_year=2026)
    session.add(topic)
    session.flush()
    return topic


def _upsert_track(session: Session, student_id: UUID, subject: Subject, current_score: int, target_score: int) -> bool:
    track = session.scalar(
        select(SubjectTrackORM)
        .where(SubjectTrackORM.student_id == student_id)
        .where(SubjectTrackORM.subject == subject)
    )
    if track is None:
        session.add(
            SubjectTrackORM(
                id=uuid4(),
                student_id=student_id,
                subject=subject,
                current_score=current_score,
                target_score=target_score,
                phase="foundation",
            )
        )
        return True
    changed = track.current_score != current_score or track.target_score != target_score
    track.current_score = current_score
    track.target_score = target_score
    return changed


def import_tracker(session: Session, path: Path | None = None, student_id: UUID = DEMO_STUDENT_ID) -> ImportSummary:
    tracker_path = path or default_tracker_path()
    if session.get(StudentProfileORM, student_id) is None:
        raise LookupError("Student profile does not exist. Run seed before importing tracker.")

    sheets = read_xlsx(tracker_path)
    summary = ImportSummary()
    summary = _import_dashboard(session, tracker_path, sheets, student_id, summary)
    summary = _import_study_log(session, tracker_path, sheets, student_id, summary)
    summary = _import_errors(session, tracker_path, sheets, student_id, summary)
    summary = _import_clean_sheet(session, tracker_path, sheets, student_id, summary)
    summary = _import_reviews(session, tracker_path, sheets, student_id, summary)
    summary = _import_score_events(session, tracker_path, sheets, student_id, summary)
    session.commit()
    return summary


def _import_dashboard(
    session: Session,
    path: Path,
    sheets: list[SheetPreview],
    student_id: UUID,
    summary: ImportSummary,
) -> ImportSummary:
    sheet = _sheet(sheets, "Дашборд")
    if sheet is None:
        return summary
    changed = 0
    for row in sheet.rows:
        subject = _subject(_cell(row, 0))
        if subject is None:
            continue
        latest_score = _int(_cell(row, 2))
        start_score = _int(_cell(row, 1))
        current_score = latest_score if latest_score is not None else start_score
        if current_score is None:
            continue
        target_score = _int(_cell(row, 3)) or 85
        if _upsert_track(session, student_id, subject, current_score, target_score):
            changed += 1
    return ImportSummary(changed, summary.study_log_entries, summary.error_events, summary.clean_sheet_events, summary.review_items, summary.score_events)


def _import_study_log(
    session: Session,
    path: Path,
    sheets: list[SheetPreview],
    student_id: UUID,
    summary: ImportSummary,
) -> ImportSummary:
    sheet = _sheet(sheets, "Дневной лог")
    if sheet is None:
        return summary
    added = 0
    for row_number, row in enumerate(sheet.rows, start=1):
        occurred_on = _date(_cell(row, 0))
        subject = _subject(_cell(row, 1))
        topic_title = _cell(row, 2)
        tasks_total = _int(_cell(row, 3))
        tasks_correct = _int(_cell(row, 4))
        if occurred_on is None or subject is None or not topic_title or tasks_total is None or tasks_correct is None:
            continue
        source_ref = _source_ref(path, sheet.name, row_number)
        if _has_source(session, StudyLogEntryORM, source_ref):
            continue
        percent = _number(_cell(row, 5))
        if percent is None:
            percent = 0.0 if tasks_total == 0 else tasks_correct / tasks_total
        session.add(
            StudyLogEntryORM(
                id=uuid4(),
                student_id=student_id,
                subject=subject,
                occurred_on=occurred_on,
                topic_title=topic_title,
                tasks_total=tasks_total,
                tasks_correct=tasks_correct,
                percent_correct=percent,
                status_note=_cell(row, 6) or None,
                note=_cell(row, 7) or None,
                source_file=str(path),
                source_sheet=sheet.name,
                source_row=row_number,
                source_ref=source_ref,
            )
        )
        added += 1
    return ImportSummary(summary.dashboard_tracks, added, summary.error_events, summary.clean_sheet_events, summary.review_items, summary.score_events)


def _import_errors(
    session: Session,
    path: Path,
    sheets: list[SheetPreview],
    student_id: UUID,
    summary: ImportSummary,
) -> ImportSummary:
    sheet = _sheet(sheets, "Журнал ошибок")
    if sheet is None:
        return summary
    added = 0
    for row_number, row in enumerate(sheet.rows, start=1):
        occurred_at = _datetime(_cell(row, 0))
        subject = _subject(_cell(row, 1))
        task_type = _cell(row, 2)
        raw_category = _cell(row, 3)
        detail = _cell(row, 4)
        if subject is None or not task_type or not raw_category:
            continue
        source_ref = _source_ref(path, sheet.name, row_number)
        if _has_source(session, ErrorEventORM, source_ref):
            continue
        topic = _topic(session, subject, task_type)
        session.add(
            ErrorEventORM(
                id=uuid4(),
                student_id=student_id,
                subject=subject,
                topic_id=topic.id,
                mission_id=None,
                attempt_id=None,
                evidence_id=None,
                category=_category(raw_category, task_type, detail),
                detail=detail or raw_category,
                created_at=occurred_at,
                source_file=str(path),
                source_sheet=sheet.name,
                source_row=row_number,
                source_ref=source_ref,
            )
        )
        added += 1
    return ImportSummary(summary.dashboard_tracks, summary.study_log_entries, added, summary.clean_sheet_events, summary.review_items, summary.score_events)


def _import_clean_sheet(
    session: Session,
    path: Path,
    sheets: list[SheetPreview],
    student_id: UUID,
    summary: ImportSummary,
) -> ImportSummary:
    sheet = _sheet(sheets, "Чистый лист")
    if sheet is None:
        return summary
    added = 0
    for row_number, row in enumerate(sheet.rows, start=1):
        occurred_on = _date(_cell(row, 0))
        tasks_total = _int(_cell(row, 1))
        clean_count = _int(_cell(row, 2))
        if occurred_on is None or tasks_total is None or clean_count is None:
            continue
        source_ref = _source_ref(path, sheet.name, row_number)
        if _has_source(session, CleanSheetEventORM, source_ref):
            continue
        session.add(
            CleanSheetEventORM(
                id=uuid4(),
                student_id=student_id,
                occurred_on=occurred_on,
                tasks_total=tasks_total,
                clean_sheet_count=clean_count,
                note=_cell(row, 4) or None,
                source_file=str(path),
                source_sheet=sheet.name,
                source_row=row_number,
                source_ref=source_ref,
            )
        )
        added += 1
    return ImportSummary(summary.dashboard_tracks, summary.study_log_entries, summary.error_events, added, summary.review_items, summary.score_events)


def _import_reviews(
    session: Session,
    path: Path,
    sheets: list[SheetPreview],
    student_id: UUID,
    summary: ImportSummary,
) -> ImportSummary:
    sheet = _sheet(sheets, "Повторение")
    if sheet is None:
        return summary
    added = 0
    for row_number, row in enumerate(sheet.rows, start=1):
        topic_title = _cell(row, 0)
        subject = _subject(_cell(row, 1))
        if not topic_title or subject is None:
            continue
        topic = _topic(session, subject, topic_title)
        for suffix, due_index, result_index in (("plus7", 3, 4), ("plus30", 5, 6)):
            due_date = _date(_cell(row, due_index))
            if due_date is None:
                continue
            source_ref = _source_ref(path, sheet.name, row_number, suffix)
            if _has_source(session, ReviewItemORM, source_ref):
                continue
            result = _cell(row, result_index).lower()
            status = ReviewStatus.DONE if "зач" in result else ReviewStatus.DUE
            session.add(
                ReviewItemORM(
                    id=uuid4(),
                    student_id=student_id,
                    topic_id=topic.id,
                    due_date=due_date,
                    status=status,
                    source_evidence_id=None,
                    source_file=str(path),
                    source_sheet=sheet.name,
                    source_row=row_number,
                    source_ref=source_ref,
                )
            )
            added += 1
    return ImportSummary(summary.dashboard_tracks, summary.study_log_entries, summary.error_events, summary.clean_sheet_events, added, summary.score_events)


def _import_score_events(
    session: Session,
    path: Path,
    sheets: list[SheetPreview],
    student_id: UUID,
    summary: ImportSummary,
) -> ImportSummary:
    sheet = _sheet(sheets, "Варианты")
    if sheet is None:
        return summary
    added = 0
    for row_number, row in enumerate(sheet.rows, start=1):
        occurred_on = _date(_cell(row, 1))
        math_score = _int(_cell(row, 2))
        info_score = _int(_cell(row, 3))
        note = _cell(row, 4) or _cell(row, 5) or None
        if occurred_on is None:
            continue
        for subject, score in ((Subject.MATH_PROFILE, math_score), (Subject.INFORMATICS, info_score)):
            if score is None:
                continue
            source_ref = _source_ref(path, sheet.name, row_number, subject.value)
            if _has_source(session, ScoreEventORM, source_ref):
                _upsert_track(session, student_id, subject, score, 85)
                continue
            session.add(
                ScoreEventORM(
                    id=uuid4(),
                    student_id=student_id,
                    subject=subject,
                    score=score,
                    kind="weekly_variant",
                    occurred_on=occurred_on,
                    note=note,
                    source_file=str(path),
                    source_sheet=sheet.name,
                    source_row=row_number,
                    source_ref=source_ref,
                )
            )
            _upsert_track(session, student_id, subject, score, 85)
            added += 1
    return ImportSummary(summary.dashboard_tracks, summary.study_log_entries, summary.error_events, summary.clean_sheet_events, summary.review_items, added)
