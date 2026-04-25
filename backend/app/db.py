from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import Settings

Base = declarative_base()


def create_db_engine(settings: Settings) -> Engine:
    connect_args: dict[str, object] = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(settings.database_url, future=True, connect_args=connect_args)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def ensure_schema_compatibility(engine: Engine) -> None:
    """Apply small SQLite-safe schema upgrades for existing MVP databases."""
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if not inspector.has_table("images"):
        return

    image_columns = {column["name"] for column in inspector.get_columns("images")}
    with engine.begin() as connection:
        if "content_hash" not in image_columns:
            connection.execute(text("ALTER TABLE images ADD COLUMN content_hash VARCHAR(64)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_images_content_hash ON images (content_hash)"))


def get_db_session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
