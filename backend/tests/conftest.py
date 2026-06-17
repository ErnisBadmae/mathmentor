import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.db import Base
from scripts import seed as seed_module


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture()
def seeded_session(session_factory, monkeypatch):
    monkeypatch.setattr(seed_module, "SessionLocal", session_factory)
    seed_module.seed()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
