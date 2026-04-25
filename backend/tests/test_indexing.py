from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from app.models import Image


def test_recursive_scan_indexes_nested_directories(scanned_client) -> None:
    container = scanned_client.app.state.container
    with container.session_factory() as session:
        images = session.execute(select(Image).where(Image.missing_at.is_(None))).scalars().all()
        relative_paths = {image.relative_path for image in images}
        assert "nested/alpha.png" in relative_paths
        assert "nested/deeper/deep.png" in relative_paths
        assert "photo.jpg" in relative_paths
        assert "nested/scan.jpeg" in relative_paths
        assert "nested/bitmap.bmp" in relative_paths


def test_incremental_reindex_updates_modified_file(scanned_client, test_paths: dict[str, Path]) -> None:
    container = scanned_client.app.state.container
    target_path = test_paths["png_root"] / "plain.png"
    original_size = target_path.stat().st_size

    target_path.write_bytes(target_path.read_bytes() + b" ")
    container.index_service.scan_now(reason="incremental")

    with container.session_factory() as session:
        image = session.execute(select(Image).where(Image.relative_path == "plain.png")).scalar_one()
        assert image.file_size_bytes != original_size
        assert image.status in {"ok", "unreadable", "corrupted"}


def test_missing_file_is_marked_missing(scanned_client, test_paths: dict[str, Path]) -> None:
    container = scanned_client.app.state.container
    (test_paths["png_root"] / "nested" / "deeper" / "deep.png").unlink()

    container.index_service.scan_now(reason="missing")

    with container.session_factory() as session:
        image = session.execute(select(Image).where(Image.relative_path == "nested/deeper/deep.png")).scalar_one()
        assert image.missing_at is not None
        assert image.status == "missing"
