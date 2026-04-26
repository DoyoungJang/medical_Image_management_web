from __future__ import annotations

from collections.abc import Iterator
from sqlite3 import Connection as SQLiteConnection

from sqlalchemy import inspect, text
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import Settings

Base = declarative_base()


def create_db_engine(settings: Settings) -> Engine:
    connect_args: dict[str, object] = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        connect_args["timeout"] = settings.sqlite_busy_timeout_seconds
    engine = create_engine(
        settings.database_url,
        future=True,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
    if settings.database_url.startswith("sqlite"):
        _configure_sqlite_connections(engine, settings)
    return engine


def _configure_sqlite_connections(engine: Engine, settings: Settings) -> None:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        if not isinstance(dbapi_connection, SQLiteConnection):
            return

        timeout_ms = max(settings.sqlite_busy_timeout_seconds, 1) * 1000
        journal_mode = _safe_sqlite_option(
            settings.sqlite_journal_mode,
            allowed={"DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"},
            default="WAL",
        )
        synchronous = _safe_sqlite_option(
            settings.sqlite_synchronous,
            allowed={"OFF", "NORMAL", "FULL", "EXTRA"},
            default="NORMAL",
        )
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute(f"PRAGMA busy_timeout={timeout_ms}")
            if journal_mode:
                cursor.execute(f"PRAGMA journal_mode={journal_mode}")
            if synchronous:
                cursor.execute(f"PRAGMA synchronous={synchronous}")
            cursor.execute("PRAGMA temp_store=MEMORY")
        finally:
            cursor.close()


def _safe_sqlite_option(raw_value: str, *, allowed: set[str], default: str) -> str:
    value = raw_value.strip().upper()
    return value if value in allowed else default


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


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
