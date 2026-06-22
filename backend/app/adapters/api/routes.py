from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.adapters.api.dependencies import get_learning_service, require_api_token
from app.adapters.api.schemas import (
    DashboardOut,
    DiagnosticOut,
    ErrorEventOut,
    ManualDecisionIn,
    ManualReviewOut,
    MentorNoteIn,
    MentorNoteOut,
    MissionCreateIn,
    MissionOut,
    MissionUpdateIn,
    ProgramPhaseOut,
    ReviewItemOut,
    ReviewResultIn,
    ScoreEventIn,
    ScoreEventOut,
    SliceDrawOut,
    SliceGradeIn,
    SliceGradeOut,
    StudentOut,
    SubmitAttemptIn,
    SubmitAttemptOut,
    TopicLifecycleOut,
)
from app.application.use_cases import LearningService
from app.domain.enums import ErrorCategory, ReviewStatus, Subject

router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(require_api_token)])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@protected_router.get("/students/current", response_model=StudentOut)
def current_student(service: LearningService = Depends(get_learning_service)) -> object:
    return service.get_current_student()


@protected_router.get("/students/{student_id}/dashboard", response_model=DashboardOut)
def dashboard(student_id: UUID, service: LearningService = Depends(get_learning_service)) -> dict[str, object]:
    return service.get_dashboard(student_id)


@protected_router.get("/students/{student_id}/missions/today", response_model=list[MissionOut])
def today_missions(student_id: UUID, service: LearningService = Depends(get_learning_service)) -> list[object]:
    return service.list_today(student_id)


@protected_router.get("/students/{student_id}/topics/lifecycle", response_model=list[TopicLifecycleOut])
def topic_lifecycle(student_id: UUID, service: LearningService = Depends(get_learning_service)) -> list[dict[str, object]]:
    return service.list_topic_lifecycle(student_id)


@protected_router.get("/students/{student_id}/program", response_model=list[ProgramPhaseOut])
def program_progress(student_id: UUID, service: LearningService = Depends(get_learning_service)) -> list[dict[str, object]]:
    return service.list_program_progress(student_id)


@protected_router.get("/students/{student_id}/diagnostics", response_model=list[DiagnosticOut])
def diagnostics(student_id: UUID, service: LearningService = Depends(get_learning_service)) -> list[dict[str, object]]:
    return service.list_diagnostics(student_id)


@protected_router.post("/students/{student_id}/missions", response_model=MissionOut)
def create_mission(
    student_id: UUID,
    payload: MissionCreateIn,
    service: LearningService = Depends(get_learning_service),
) -> object:
    values = payload.model_dump()
    values["student_id"] = student_id
    return service.create_mission(values)


@protected_router.patch("/missions/{mission_id}", response_model=MissionOut)
def update_mission(
    mission_id: UUID,
    payload: MissionUpdateIn,
    service: LearningService = Depends(get_learning_service),
) -> object:
    return service.update_mission(mission_id, payload.model_dump(exclude_unset=True))


@protected_router.get("/students/{student_id}/errors", response_model=list[ErrorEventOut])
def error_journal(
    student_id: UUID,
    subject: Subject | None = None,
    category: ErrorCategory | None = None,
    service: LearningService = Depends(get_learning_service),
) -> list[dict[str, object]]:
    return service.list_errors(student_id, subject=subject, category=category)


@protected_router.get("/students/{student_id}/reviews", response_model=list[ReviewItemOut])
def review_queue(
    student_id: UUID,
    status: ReviewStatus | None = None,
    due_only: bool = False,
    service: LearningService = Depends(get_learning_service),
) -> list[dict[str, object]]:
    return service.list_reviews(student_id, status=status, due_only=due_only)


@protected_router.post("/reviews/{review_id}/result", response_model=ReviewItemOut)
def review_result(
    review_id: UUID,
    payload: ReviewResultIn,
    service: LearningService = Depends(get_learning_service),
) -> object:
    return service.record_review_result(review_id, payload.passed)


@protected_router.get("/students/{student_id}/manual-reviews", response_model=list[ManualReviewOut])
def manual_reviews(
    student_id: UUID,
    service: LearningService = Depends(get_learning_service),
) -> list[dict[str, object]]:
    return service.list_manual_reviews(student_id)


@protected_router.post("/evidence/{evidence_id}/manual-decision", response_model=SubmitAttemptOut)
def manual_decision(
    evidence_id: UUID,
    payload: ManualDecisionIn,
    service: LearningService = Depends(get_learning_service),
) -> dict[str, object]:
    return service.apply_manual_decision(evidence_id, payload.model_dump(exclude_unset=True))


@protected_router.post("/students/{student_id}/score-events", response_model=ScoreEventOut)
def score_event(
    student_id: UUID,
    payload: ScoreEventIn,
    service: LearningService = Depends(get_learning_service),
) -> object:
    return service.record_score_event({**payload.model_dump(), "student_id": student_id})


@protected_router.post("/students/{student_id}/mentor-notes", response_model=MentorNoteOut)
def publish_mentor_note(
    student_id: UUID,
    payload: MentorNoteIn,
    service: LearningService = Depends(get_learning_service),
) -> object:
    return service.publish_feedback({**payload.model_dump(), "student_id": student_id})


@protected_router.get("/students/{student_id}/slices/draw", response_model=SliceDrawOut)
def draw_slice(
    student_id: UUID,
    subject: Subject = Subject.MATH_PROFILE,
    size: int = Query(default=8, ge=1, le=50),
    service: LearningService = Depends(get_learning_service),
) -> dict[str, object]:
    return {"subject": subject, "items": service.draw_slice(subject, size)}


@protected_router.post("/students/{student_id}/slices/grade", response_model=SliceGradeOut)
def grade_slice(
    student_id: UUID,
    payload: SliceGradeIn,
    service: LearningService = Depends(get_learning_service),
) -> dict[str, object]:
    items = [item.model_dump() for item in payload.items]
    return service.grade_slice(student_id, payload.subject, items)


@protected_router.post("/attempts", response_model=SubmitAttemptOut)
async def submit_attempt(
    payload: SubmitAttemptIn,
    service: LearningService = Depends(get_learning_service),
) -> dict[str, object]:
    return await service.submit_attempt(payload.model_dump())


router.include_router(protected_router)
