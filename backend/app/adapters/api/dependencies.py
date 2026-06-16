from collections.abc import Generator

from sqlalchemy.orm import Session

from app.application.use_cases import LearningService, RuleBasedReviewer
from app.config import get_settings
from app.infrastructure.db import get_session
from app.infrastructure.llm import OpenAICompatibleReviewer
from app.infrastructure.repositories import SqlAlchemyUnitOfWork


def get_learning_service() -> Generator[LearningService, None, None]:
    session: Session = next(get_session())
    try:
        settings = get_settings()
        reviewer = OpenAICompatibleReviewer(settings) if settings.llm_provider == "openai_compatible" else RuleBasedReviewer()
        yield LearningService(SqlAlchemyUnitOfWork(session), reviewer)
    finally:
        session.close()
