from __future__ import annotations

from app.core.config import Settings


def test_cors_origins_accepts_comma_separated_env(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:8080")

    settings = Settings()

    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:8080"]


def test_cors_origins_accepts_json_array_env(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:5173", "http://127.0.0.1:8080"]')

    settings = Settings()

    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:8080"]
