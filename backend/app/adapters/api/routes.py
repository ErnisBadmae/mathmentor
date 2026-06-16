from uuid import UUID

from fastapi import APIRouter, Depends

from app.adapters.api.dependencies import get_learning_service
from app.adapters.api.schemas import DashboardOut, MissionOut, SubmitAttemptIn, SubmitAttemptOut
from app.application.use_cases import LearningService

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/students/{student_id}/dashboard", response_model=DashboardOut)
def dashboard(student_id: UUID, service: LearningService = Depends(get_learning_service)) -> dict[str, object]:
    return service.get_dashboard(student_id)


@router.get("/students/{student_id}/missions/today", response_model=list[MissionOut])
def today_missions(student_id: UUID, service: LearningService = Depends(get_learning_service)) -> list[object]:
    return service.list_today(student_id)


@router.post("/attempts", response_model=SubmitAttemptOut)
async def submit_attempt(payload: SubmitAttemptIn, service: LearningService = Depends(get_learning_service)) -> dict[str, object]:
    return await service.submit_attempt(payload.model_dump())
