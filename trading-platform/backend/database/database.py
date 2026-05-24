from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.config.settings import get_settings
from backend.database.base import Base
from backend.utils.logger import get_logger


settings = get_settings()
logger = get_logger(__name__)
DATABASE_URL = settings.database_url or "sqlite:///./trading_platform.db"


def _create_engine() -> Engine:
    engine_args: dict = {"pool_pre_ping": True}
    if DATABASE_URL.startswith("sqlite"):
        engine_args["connect_args"] = {"check_same_thread": False}
    else:
        engine_args.update({"pool_size": 10, "max_overflow": 20})
    return create_engine(DATABASE_URL, **engine_args)


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


def get_db():
    """FastAPI dependency for database sessions."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> bool:
    """Safely initialize declared tables without running migrations."""

    try:
        from backend.database import models  # noqa: F401

        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized")
        return True
    except SQLAlchemyError as exc:
        logger.error("Database initialization failed: %s", exc)
        return False


def close_db() -> None:
    """Dispose database connections during shutdown or tooling operations."""

    engine.dispose()
