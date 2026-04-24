from __future__ import annotations

import zlib
from pathlib import Path

import bcrypt
import pytest
from fastapi.testclient import TestClient
from PIL import Image, PngImagePlugin

from app.core.config import Settings
from app.main import create_app


def _create_png(path: Path, *, size: tuple[int, int], color, pnginfo: PngImagePlugin.PngInfo | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA" if len(color) == 4 else "RGB", size, color=color)
    image.save(path, format="PNG", pnginfo=pnginfo)


def create_test_png_tree(root: Path) -> None:
    info = PngImagePlugin.PngInfo()
    info.add_text("Author", "홍길동")
    info.add_text("CompressedNote", "압축된 메타데이터", zip=True)
    info.add_itxt("Description", "검색 가능한 PNG 설명", lang="ko")

    _create_png(root / "plain.png", size=(64, 32), color=(255, 0, 0))
    _create_png(root / "meta.png", size=(80, 80), color=(0, 255, 0), pnginfo=info)
    _create_png(root / "nested" / "alpha.png", size=(40, 50), color=(0, 0, 255, 128))
    _create_png(root / "nested" / "deeper" / "deep.png", size=(120, 60), color=(255, 255, 0))
    (root / "broken.png").write_bytes(b"\x89PNG\r\n\x1a\n" + zlib.compress(b"not-a-real-png"))


@pytest.fixture()
def test_paths(tmp_path: Path) -> dict[str, Path]:
    png_root = tmp_path / "png-root"
    png_root.mkdir()
    thumbnail_cache = tmp_path / "thumb-cache"
    thumbnail_cache.mkdir()
    database_path = tmp_path / "app.db"

    create_test_png_tree(png_root)
    return {
        "png_root": png_root,
        "thumbnail_cache": thumbnail_cache,
        "database_path": database_path,
    }


@pytest.fixture()
def settings(test_paths: dict[str, Path]) -> Settings:
    password_hash = bcrypt.hashpw(b"secret123", bcrypt.gensalt()).decode("utf-8")
    return Settings(
        environment="test",
        png_root_dir=str(test_paths["png_root"]),
        thumbnail_cache_dir=str(test_paths["thumbnail_cache"]),
        database_url=f"sqlite:///{test_paths['database_path'].as_posix()}",
        auto_scan_on_startup=False,
        auth_enabled=True,
        auth_username="admin",
        auth_password_hash=password_hash,
        auth_secret_key="test-secret-key",
        cors_origins=["http://localhost:5173"],
    )


@pytest.fixture()
def app(settings: Settings):
    return create_app(settings)


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def authenticated_client(client: TestClient) -> TestClient:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
    assert response.status_code == 200
    return client


@pytest.fixture()
def scanned_client(authenticated_client: TestClient) -> TestClient:
    container = authenticated_client.app.state.container
    container.index_service.scan_now(reason="test-setup")
    return authenticated_client
