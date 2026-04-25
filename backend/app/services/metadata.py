from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, UnidentifiedImageError

from app.core.config import Settings
from app.services.png_chunks import PNGChunkInfo, PNGChunkParser, PNGChunkParserError


SUPPORTED_PIL_FORMATS = {
    "PNG",
    "JPEG",
    "BMP",
    "GIF",
    "TIFF",
    "WEBP",
    "ICO",
    "JPEG2000",
    "TGA",
}


@dataclass(slots=True)
class MetadataPair:
    key: str
    value_text: str
    value_number: float | None = None


@dataclass(slots=True)
class ExtractedMetadata:
    relative_path: str
    filename: str
    directory: str
    extension: str
    file_size_bytes: int
    modified_time: datetime
    width: int | None
    height: int | None
    format: str | None
    mode: str | None
    bit_depth: int | None
    color_type: str | None
    has_alpha: bool | None
    dpi_x: float | None
    dpi_y: float | None
    status: str
    error_message: str | None
    metadata: dict[str, Any]
    metadata_pairs: list[MetadataPair] = field(default_factory=list)
    metadata_text: str = ""


class MetadataExtractor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.chunk_parser = PNGChunkParser(max_text_bytes=settings.max_png_text_bytes)

    def extract(self, path: Path, relative_path: str, stat_result: object | None = None) -> ExtractedMetadata:
        filename = Path(relative_path).name
        directory = str(Path(relative_path).parent).replace("\\", "/")
        if directory == ".":
            directory = ""
        extension = Path(relative_path).suffix.lower()
        stat_info = stat_result if stat_result is not None else path.stat()
        modified_time = datetime.fromtimestamp(stat_info.st_mtime, tz=timezone.utc)
        file_size_bytes = int(stat_info.st_size)

        base = {
            "relative_path": relative_path,
            "filename": filename,
            "directory": directory,
            "extension": extension,
            "file_size_bytes": file_size_bytes,
            "modified_time": modified_time,
        }

        try:
            with Image.open(path) as image:
                image.load()
                image_format = (image.format or "").upper()
                if image_format and image_format not in SUPPORTED_PIL_FORMATS:
                    return self._unsupported(base, "지원하지 않는 이미지 형식입니다.")

                chunk_info = self._parse_png_chunks_if_applicable(path, image_format)
                dpi_x, dpi_y = self._extract_dpi(image.info.get("dpi"))
                has_alpha = self._has_alpha(image)
                pillow_info = self._sanitize_mapping(image.info)
                exif_metadata = self._extract_exif(image)
                xmp_metadata = self._extract_xmp_from_info(image.info)
                textual_metadata = self._collect_textual_metadata(chunk_info.text_chunks, pillow_info)
                bit_depth = chunk_info.bit_depth or self._extract_bit_depth(image, pillow_info)
                color_type = chunk_info.color_type or self._extract_color_type(image)
                metadata = {
                    "relative_path": relative_path,
                    "filename": filename,
                    "directory": directory,
                    "extension": extension,
                    "file_size_bytes": file_size_bytes,
                    "modified_time": modified_time.isoformat(),
                    "width": image.width,
                    "height": image.height,
                    "format": image.format,
                    "mode": image.mode,
                    "bit_depth": bit_depth,
                    "color_type": color_type,
                    "has_alpha": has_alpha,
                    "dpi": {"x": dpi_x, "y": dpi_y},
                    "gamma": pillow_info.get("gamma", chunk_info.gamma),
                    "icc_profile": {
                        "present": chunk_info.icc_profile_present or "icc_profile" in image.info,
                        "summary": self._icc_profile_summary(image.info, chunk_info.icc_profile_summary),
                    },
                    "text_chunks": chunk_info.text_chunks,
                    "textual_metadata": textual_metadata,
                    "exif_present": chunk_info.exif_present or bool(image.info.get("exif")),
                    "exif": exif_metadata,
                    "xmp_present": bool(xmp_metadata),
                    "xmp": xmp_metadata,
                    "pillow_info": pillow_info,
                }

                pairs = self._build_metadata_pairs(metadata)
                metadata_text = self._build_metadata_text(relative_path, pairs)

                return ExtractedMetadata(
                    **base,
                    width=image.width,
                    height=image.height,
                    format=image.format,
                    mode=image.mode,
                    bit_depth=bit_depth,
                    color_type=color_type,
                    has_alpha=has_alpha,
                    dpi_x=dpi_x,
                    dpi_y=dpi_y,
                    status="ok",
                    error_message=None,
                    metadata=metadata,
                    metadata_pairs=pairs,
                    metadata_text=metadata_text,
                )
        except UnidentifiedImageError as exc:
            return self._failure(base, "corrupted", exc)
        except PNGChunkParserError as exc:
            return self._failure(base, "corrupted", exc)
        except PermissionError as exc:
            return self._failure(base, "unreadable", exc)
        except OSError as exc:
            return self._failure(base, "unreadable", exc)
        except Exception as exc:  # pragma: no cover - defensive fallback
            return self._failure(base, "unreadable", exc)

    def _parse_png_chunks_if_applicable(self, path: Path, image_format: str) -> PNGChunkInfo:
        if image_format != "PNG":
            return PNGChunkInfo()
        return self.chunk_parser.parse(path)

    def _unsupported(self, base: dict[str, Any], message: str) -> ExtractedMetadata:
        return ExtractedMetadata(
            **base,
            width=None,
            height=None,
            format=None,
            mode=None,
            bit_depth=None,
            color_type=None,
            has_alpha=None,
            dpi_x=None,
            dpi_y=None,
            status="unsupported",
            error_message=message,
            metadata={"message": message},
            metadata_pairs=[],
            metadata_text=message,
        )

    def _failure(self, base: dict[str, Any], status: str, exc: Exception) -> ExtractedMetadata:
        message = str(exc).replace(str(base["relative_path"]), Path(base["relative_path"]).name)
        metadata = {
            "relative_path": base["relative_path"],
            "filename": base["filename"],
            "directory": base["directory"],
            "error": message,
        }
        return ExtractedMetadata(
            **base,
            width=None,
            height=None,
            format=Path(base["relative_path"]).suffix.lower().lstrip(".").upper() or None,
            mode=None,
            bit_depth=None,
            color_type=None,
            has_alpha=None,
            dpi_x=None,
            dpi_y=None,
            status=status,
            error_message=message,
            metadata=metadata,
            metadata_pairs=self._build_metadata_pairs(metadata),
            metadata_text=self._build_metadata_text(base["relative_path"], self._build_metadata_pairs(metadata)),
        )

    def _extract_dpi(self, dpi_value: Any) -> tuple[float | None, float | None]:
        if not dpi_value:
            return None, None
        if isinstance(dpi_value, tuple) and len(dpi_value) >= 2:
            return self._safe_float(dpi_value[0]), self._safe_float(dpi_value[1])
        return None, None

    def _icc_profile_summary(self, image_info: dict[str, Any], parser_summary: str | None) -> str | None:
        if parser_summary:
            return parser_summary
        icc_profile = image_info.get("icc_profile")
        if isinstance(icc_profile, bytes):
            return f"ICC profile present ({len(icc_profile)} bytes)"
        if isinstance(icc_profile, str):
            return f"ICC profile present ({len(icc_profile.encode('utf-8'))} bytes)"
        return None

    def _extract_bit_depth(self, image: Image.Image, pillow_info: dict[str, Any]) -> int | None:
        bits_value = pillow_info.get("bits") or pillow_info.get("bits_per_sample")
        safe_bits = self._safe_float(bits_value)
        if safe_bits is not None:
            return int(safe_bits)
        mode = image.mode
        if mode == "1":
            return 1
        if mode in {"L", "P", "RGB", "RGBA", "LA", "CMYK", "YCbCr"}:
            return 8
        if mode.startswith("I;16"):
            return 16
        if mode in {"I", "F"}:
            return 32
        return None

    def _extract_color_type(self, image: Image.Image) -> str:
        mode_labels = {
            "1": "binary",
            "L": "grayscale",
            "LA": "grayscale-alpha",
            "P": "palette",
            "RGB": "truecolor",
            "RGBA": "truecolor-alpha",
            "CMYK": "cmyk",
            "YCbCr": "ycbcr",
            "I": "integer",
            "F": "float",
        }
        return mode_labels.get(image.mode, image.mode.lower())

    def _extract_exif(self, image: Image.Image) -> dict[str, Any]:
        try:
            raw_exif = image.getexif()
        except Exception:
            return {}
        if not raw_exif:
            return {}
        metadata: dict[str, Any] = {}
        for tag_id, value in raw_exif.items():
            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
            metadata[str(tag_name)] = self._sanitize_value(value)
        return metadata

    def _extract_xmp_from_info(self, image_info: dict[str, Any]) -> dict[str, Any]:
        combined_fields: dict[str, list[str]] = {}
        raw_values: list[str] = []
        for key, value in image_info.items():
            normalized_key = str(key).lower()
            if "xmp" not in normalized_key and normalized_key not in {"xml", "xml_packet"}:
                continue
            extracted = self._extract_xmp(value)
            fields = extracted.get("fields")
            if isinstance(fields, dict):
                for field_key, field_values in fields.items():
                    if not isinstance(field_values, list):
                        continue
                    bucket = combined_fields.setdefault(str(field_key), [])
                    for field_value in field_values:
                        text_value = str(field_value).strip()
                        if text_value and text_value not in bucket:
                            bucket.append(text_value)
            raw_value = extracted.get("raw")
            if isinstance(raw_value, str) and raw_value not in raw_values:
                raw_values.append(raw_value)

        metadata: dict[str, Any] = {}
        if combined_fields:
            metadata["fields"] = combined_fields
        if raw_values:
            metadata["raw"] = raw_values
        return metadata

    def _extract_xmp(self, xmp_value: Any) -> dict[str, Any]:
        if not xmp_value:
            return {}
        if isinstance(xmp_value, bytes):
            xmp_text = xmp_value.decode("utf-8", errors="replace")
        else:
            xmp_text = str(xmp_value)

        fields: dict[str, list[str]] = {}
        try:
            root = ET.fromstring(xmp_text)
        except ET.ParseError:
            return {"raw": xmp_text[:4000]}

        def local_name(name: str) -> str:
            if "}" in name:
                return name.rsplit("}", 1)[1]
            if ":" in name:
                return name.rsplit(":", 1)[1]
            return name

        def add_field(key: str, value: Any) -> None:
            text_value = str(value).strip()
            if not key or not text_value:
                return
            bucket = fields.setdefault(key, [])
            if text_value not in bucket:
                bucket.append(text_value)

        for element in root.iter():
            text_value = (element.text or "").strip()
            if text_value:
                add_field(local_name(element.tag), text_value)
            for attribute_name, attribute_value in element.attrib.items():
                if local_name(attribute_name) == "about":
                    continue
                add_field(local_name(attribute_name), attribute_value)
        return {"fields": fields}

    def _has_alpha(self, image: Image.Image) -> bool:
        if "A" in image.mode:
            return True
        if image.mode == "P":
            return "transparency" in image.info
        return False

    def _sanitize_mapping(self, mapping: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in mapping.items():
            sanitized[key] = self._sanitize_value(value)
        return sanitized

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, bytes):
            return f"<{len(value)} bytes>"
        if isinstance(value, dict):
            return {str(key): self._sanitize_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._sanitize_value(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    def _collect_textual_metadata(self, text_chunks: list[dict[str, str]], pillow_info: dict[str, Any]) -> dict[str, list[str]]:
        textual: dict[str, list[str]] = {}

        def add_value(key: str, value: str) -> None:
            bucket = textual.setdefault(key, [])
            if value not in bucket:
                bucket.append(value)

        for item in text_chunks:
            add_value(item["key"], item.get("value", ""))
        for key, value in pillow_info.items():
            if key in {"dpi", "gamma", "icc_profile", "exif"}:
                continue
            if isinstance(value, str) and value:
                add_value(key, value)
        return textual

    def _build_metadata_pairs(self, metadata: dict[str, Any]) -> list[MetadataPair]:
        pairs: list[MetadataPair] = []

        def add_pair(key: str, value: Any) -> None:
            if value is None:
                return
            if isinstance(value, bool):
                pairs.append(MetadataPair(key=key, value_text=str(value).lower(), value_number=1.0 if value else 0.0))
                return
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                pairs.append(MetadataPair(key=key, value_text=str(value), value_number=float(value)))
                return
            if isinstance(value, str):
                trimmed = value.strip()
                if trimmed:
                    pairs.append(MetadataPair(key=key, value_text=trimmed[:1000], value_number=self._safe_float(trimmed)))
                return
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    add_pair(f"{key}.{nested_key}" if key else str(nested_key), nested_value)
                return
            if isinstance(value, list):
                for index, nested_value in enumerate(value):
                    if isinstance(nested_value, dict):
                        for nested_key, list_value in nested_value.items():
                            add_pair(f"{key}.{index}.{nested_key}", list_value)
                    else:
                        add_pair(key, nested_value)
                return

            add_pair(key, str(value))

        add_pair("", metadata)
        deduped: dict[tuple[str, str], MetadataPair] = {}
        for pair in pairs:
            if pair.key:
                deduped[(pair.key, pair.value_text)] = pair
        return list(deduped.values())

    def _build_metadata_text(self, relative_path: str, pairs: list[MetadataPair]) -> str:
        fragments = [relative_path]
        for pair in pairs:
            fragments.append(pair.key)
            fragments.append(pair.value_text)
        combined = "\n".join(fragment for fragment in fragments if fragment)
        return combined[: self.settings.max_metadata_text_length]

    def serialize_metadata(self, metadata: dict[str, Any]) -> str:
        return json.dumps(metadata, ensure_ascii=False, sort_keys=True)

    def deserialize_metadata(self, metadata_json: str) -> dict[str, Any]:
        return json.loads(metadata_json) if metadata_json else {}

    def _safe_float(self, value: Any) -> float | None:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if math.isfinite(numeric):
            return numeric
        return None
