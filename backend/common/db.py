import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.common.config import settings


def _build_database_url() -> str:
    database_url = (settings.DATABASE_URL or "").strip()
    if database_url:
        return _normalize_database_url(database_url)

    required_env_names = ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME")
    missing_env_names = [
        env_name
        for env_name in required_env_names
        if not (os.getenv(env_name) or "").strip()
    ]
    if missing_env_names:
        missing_env_text = ", ".join(missing_env_names)
        raise RuntimeError(
            "Database configuration is missing. "
            f"Set DATABASE_URL or all required DB env vars: {missing_env_text}"
        )

    return (
        f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("mysql+pymysql://"):
        return database_url.replace("mysql+pymysql://", "postgresql+psycopg2://", 1)
    if database_url.startswith("mysql://"):
        return database_url.replace("mysql://", "postgresql+psycopg2://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return database_url


SQLALCHEMY_DATABASE_URL = _build_database_url()

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.ENV == "development"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
