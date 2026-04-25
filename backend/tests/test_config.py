from __future__ import annotations

from app.core.config import Settings


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
