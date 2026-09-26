from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from app.config import settings

# Engine configuration
connect_args = {}
if settings.is_sqlite:
    connect_args["check_same_thread"] = False

# Create engine with SQLAlchemy 2.x standard configuration
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True if not settings.is_sqlite else False,
)

# SessionLocal class for instantiating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass


# FastAPI dependency to yield database sessions
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
