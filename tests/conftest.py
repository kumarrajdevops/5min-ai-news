import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base


@pytest.fixture
def db_session():
    """
    A real SQLAlchemy session backed by an in-memory SQLite database,
    for testing functions that take `db` as an explicit parameter
    (e.g. app.tasks.episode_video._produce_story_content) without
    touching the real Postgres database.

    Deliberately not the app's own Postgres engine -- every model in
    app/models.py uses portable column types (String/Integer/Float/
    DateTime/Text/ForeignKey/UniqueConstraint), so SQLite is a faithful
    stand-in and keeps the test suite dependency-free (no running
    Postgres required to run `pytest`). SQLAlchemy raises the same
    IntegrityError on a unique-constraint violation regardless of
    backend, which is what the ingestion race-condition test relies on.
    """

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()
