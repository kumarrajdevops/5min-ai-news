from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


DATABASE_URL = (
    f"postgresql+psycopg://{settings.postgres_user}:"
    f"{settings.postgres_password}@{settings.postgres_host}:"
    f"{settings.postgres_port}/{settings.postgres_db}"
)


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# NOTE: there is deliberately no init_db()/create_all() here anymore.
# Schema management is Alembic's job exclusively -- run
# `alembic upgrade head` before starting the app. See app/main.py's
# startup() docstring for why this matters (create_all() vs Alembic
# version tracking used to conflict and break migrations).