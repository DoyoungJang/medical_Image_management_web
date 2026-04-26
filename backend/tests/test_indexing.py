from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import select

from app.models import Image, MetadataKV
from app.services import filesystem as filesystem_module


def test_recursive_scan_indexes_nested_directories(scanned_client) -> None:
    container = scanned_client.app.state.container
    with container.session_factory() as session:
        images = session.execute(select(Image).where(Image.missing_at.is_(None))).scalars().all()
        relative_paths = {image.relative_path for image in images}
        assert "nested/alpha.png" in relative_paths
        assert "nested/deeper/deep.png" in relative_paths
        assert "photo.jpg" in relative_paths
        assert "jpeg-disguised-as-png.png" in relative_paths
        assert "nested/scan.jpeg" in relative_paths
        assert "nested/bitmap.bmp" in relative_paths
        assert "animated.gif" in relative_paths
        assert "nested/slice.tiff" in relative_paths
        assert "nested/preview.webp" in relative_paths


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


def test_incremental_reindex_skips_unchanged_files(scanned_client) -> None:
    container = scanned_client.app.state.container

    result = container.index_service.scan_now(reason="unchanged")

    assert result.updated == 0
    assert result.missing_marked == 0
    assert result.scanned == result.skipped


def test_incremental_reindex_updates_when_metadata_changes_but_stat_is_same(scanned_client, test_paths: dict[str, Path]) -> None:
    container = scanned_client.app.state.container
    target_path = test_paths["png_root"] / "photo.jpg"
    original_stat = target_path.stat()
    original_bytes = target_path.read_bytes()
    updated_bytes = original_bytes.replace(b"<custom:View>4CV</custom:View>", b"<custom:View>5CV</custom:View>")

    assert updated_bytes != original_bytes
    assert len(updated_bytes) == len(original_bytes)

    target_path.write_bytes(updated_bytes)
    os.utime(target_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))

    result = container.index_service.scan_now(reason="metadata-changed")

    assert result.updated >= 1
    assert result.skipped < result.scanned
    with container.session_factory() as session:
        image = session.execute(select(Image).where(Image.relative_path == "photo.jpg")).scalar_one()
        metadata_value = session.execute(
            select(MetadataKV.value_text).where(MetadataKV.image_id == image.id, MetadataKV.key == "xmp.fields.View")
        ).scalar_one()
        assert metadata_value == "5CV"


def test_missing_file_is_marked_missing(scanned_client, test_paths: dict[str, Path]) -> None:
    container = scanned_client.app.state.container
    (test_paths["png_root"] / "nested" / "deeper" / "deep.png").unlink()

    container.index_service.scan_now(reason="missing")

    with container.session_factory() as session:
        image = session.execute(select(Image).where(Image.relative_path == "nested/deeper/deep.png")).scalar_one()
        assert image.missing_at is not None
        assert image.status == "missing"


def test_scan_skips_unreadable_directory_without_crashing(scanned_client, test_paths: dict[str, Path], monkeypatch) -> None:
    container = scanned_client.app.state.container
    original_scandir = filesystem_module.os.scandir

    def guarded_scandir(path):
        if Path(path).name == "deeper":
            raise PermissionError("access denied")
        return original_scandir(path)

    monkeypatch.setattr(filesystem_module.os, "scandir", guarded_scandir)

    result = container.index_service.scan_now(reason="permission-skip")

    assert result.scanned > 0
