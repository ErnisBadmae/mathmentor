from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.application.use_cases import LearningService, RuleBasedReviewer
from app.config import get_settings
from app.infrastructure.db import get_session
from app.infrastructure.llm import OpenAICompatibleReviewer
from app.infrastructure.repositories import SqlAlchemyUnitOfWork


def require_api_token(
    x_ege_mentor_token: Annotated[str | None, Header(alias="X-EGE-MENTOR-TOKEN")] = None,
) -> None:
    expected = get_settings().api_shared_token
    if expected and x_ege_mentor_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token")


def get_learning_service(session: Session = Depends(get_session)) -> Generator[LearningService, None, None]:
    settings = get_settings()
    connection = settings.llm_connection()
    reviewer = OpenAICompatibleReviewer(connection) if connection else RuleBasedReviewer()
    yield LearningService(SqlAlchemyUnitOfWork(session), reviewer, settings.local_timezone)
