from __future__ import annotations

from sqlalchemy import text

from app.core.config import Settings
from app.db import create_db_engine


def test_cors_origins_accepts_comma_separated_env(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:8080")

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:8080"]


def test_cors_origins_accepts_json_array_env(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:5173", "http://127.0.0.1:8080"]')

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:8080"]


def test_supported_image_extensions_accepts_comma_separated_env(monkeypatch) -> None:
    monkeypatch.setenv("SUPPORTED_IMAGE_EXTENSIONS", "png,jpg,.jpeg,bmp")

    settings = Settings()

    assert settings.supported_image_extensions == [".png", ".jpg", ".jpeg", ".bmp"]


def test_supported_image_extensions_default_includes_common_formats(monkeypatch) -> None:
    monkeypatch.delenv("SUPPORTED_IMAGE_EXTENSIONS", raising=False)

    settings = Settings(_env_file=None)

    assert {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp", ".ico"}.issubset(
        set(settings.supported_image_extensions)
    )


def test_sqlite_engine_uses_concurrency_pragmas(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{(tmp_path / 'concurrency.db').as_posix()}",
        sqlite_busy_timeout_seconds=7,
        sqlite_journal_mode="WAL",
        sqlite_synchronous="NORMAL",
    )
    engine = create_db_engine(settings)

    with engine.connect() as connection:
        busy_timeout = connection.execute(text("PRAGMA busy_timeout")).scalar_one()
        journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()

    assert busy_timeout == 7000
    assert str(journal_mode).lower() == "wal"
