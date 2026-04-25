from __future__ import annotations

from pathlib import Path

from app.services.metadata import MetadataExtractor
from app.services.png_chunks import PNGChunkParser


def test_png_text_chunks_are_parsed(settings, test_paths: dict[str, Path]) -> None:
    parser = PNGChunkParser()
    chunk_info = parser.parse(test_paths["png_root"] / "meta.png")

    keys = {item["key"] for item in chunk_info.text_chunks}
    assert {"Author", "CompressedNote", "Description"}.issubset(keys)
    assert chunk_info.bit_depth == 8
    assert chunk_info.color_type == "truecolor"


def test_metadata_extractor_collects_dimensions_alpha_and_text(settings, test_paths: dict[str, Path]) -> None:
    extractor = MetadataExtractor(settings)

    alpha_metadata = extractor.extract(test_paths["png_root"] / "nested" / "alpha.png", "nested/alpha.png")
    meta_metadata = extractor.extract(test_paths["png_root"] / "meta.png", "meta.png")

    assert alpha_metadata.has_alpha is True
    assert alpha_metadata.width == 40
    assert alpha_metadata.height == 50
    assert meta_metadata.status == "ok"
    assert meta_metadata.metadata["textual_metadata"]["Author"] == ["홍길동"]
    pair_keys = {pair.key for pair in meta_metadata.metadata_pairs}
    assert "textual_metadata.Author" in pair_keys


def test_metadata_extractor_supports_jpeg_and_bmp(settings, test_paths: dict[str, Path]) -> None:
    extractor = MetadataExtractor(settings)

    jpg_metadata = extractor.extract(test_paths["png_root"] / "photo.jpg", "photo.jpg")
    bmp_metadata = extractor.extract(test_paths["png_root"] / "nested" / "bitmap.bmp", "nested/bitmap.bmp")

    assert jpg_metadata.status == "ok"
    assert jpg_metadata.format == "JPEG"
    assert jpg_metadata.extension == ".jpg"
    assert jpg_metadata.width == 72
    assert jpg_metadata.height == 48
    assert bmp_metadata.status == "ok"
    assert bmp_metadata.format == "BMP"
    assert bmp_metadata.extension == ".bmp"
    assert bmp_metadata.width == 32
    assert bmp_metadata.height == 24


def test_corrupted_png_is_marked_as_corrupted(settings, test_paths: dict[str, Path]) -> None:
    extractor = MetadataExtractor(settings)
    corrupted_metadata = extractor.extract(test_paths["png_root"] / "broken.png", "broken.png")
    assert corrupted_metadata.status == "corrupted"
    assert corrupted_metadata.error_message is not None
