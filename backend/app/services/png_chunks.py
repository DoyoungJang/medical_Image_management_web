from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
CHUNK_HEADER_SIZE = 8
CHUNK_CRC_SIZE = 4
MAX_CHUNK_LENGTH = 16 * 1024 * 1024

COLOR_TYPE_MAP = {
    0: "grayscale",
    2: "truecolor",
    3: "indexed-color",
    4: "grayscale-alpha",
    6: "truecolor-alpha",
}


@dataclass(slots=True)
class PNGChunkInfo:
    bit_depth: int | None = None
    color_type: str | None = None
    gamma: float | None = None
    icc_profile_present: bool = False
    icc_profile_summary: str | None = None
    exif_present: bool = False
    text_chunks: list[dict[str, str]] = field(default_factory=list)


class PNGChunkParserError(ValueError):
    """Raised when the PNG chunk parser encounters an invalid PNG."""


class PNGChunkParser:
    def __init__(self, *, max_text_bytes: int = 512_000) -> None:
        self.max_text_bytes = max_text_bytes

    def parse(self, path: Path) -> PNGChunkInfo:
        info = PNGChunkInfo()
        text_budget = self.max_text_bytes

        with path.open("rb") as file_handle:
            signature = file_handle.read(len(PNG_SIGNATURE))
            if signature != PNG_SIGNATURE:
                raise PNGChunkParserError("Invalid PNG signature.")

            while True:
                raw_length = file_handle.read(4)
                if len(raw_length) == 0:
                    break
                if len(raw_length) != 4:
                    raise PNGChunkParserError("Incomplete PNG chunk length.")

                (chunk_length,) = struct.unpack(">I", raw_length)
                if chunk_length > MAX_CHUNK_LENGTH:
                    raise PNGChunkParserError("Chunk length exceeds safety limit.")

                chunk_type = file_handle.read(4)
                if len(chunk_type) != 4:
                    raise PNGChunkParserError("Incomplete PNG chunk type.")

                chunk_data = file_handle.read(chunk_length)
                if len(chunk_data) != chunk_length:
                    raise PNGChunkParserError("Incomplete PNG chunk data.")

                crc = file_handle.read(CHUNK_CRC_SIZE)
                if len(crc) != CHUNK_CRC_SIZE:
                    raise PNGChunkParserError("Incomplete PNG chunk CRC.")

                chunk_name = chunk_type.decode("ascii", errors="replace")
                if chunk_name == "IHDR":
                    self._parse_ihdr(chunk_data, info)
                elif chunk_name == "gAMA":
                    info.gamma = self._parse_gamma(chunk_data)
                elif chunk_name == "iCCP":
                    info.icc_profile_present = True
                    info.icc_profile_summary = self._parse_iccp(chunk_data)
                elif chunk_name == "eXIf":
                    info.exif_present = True
                elif chunk_name in {"tEXt", "zTXt", "iTXt"} and text_budget > 0:
                    try:
                        parsed = self._parse_text_chunk(chunk_name, chunk_data, text_budget)
                    except (ValueError, zlib.error):
                        parsed = None
                    if parsed is not None:
                        info.text_chunks.append(parsed)
                        text_budget -= len(parsed.get("value", "").encode("utf-8", errors="ignore"))
                elif chunk_name == "IEND":
                    break

        return info

    def _parse_ihdr(self, chunk_data: bytes, info: PNGChunkInfo) -> None:
        if len(chunk_data) != 13:
            raise PNGChunkParserError("IHDR chunk length is invalid.")
        _, _, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", chunk_data)
        info.bit_depth = bit_depth
        info.color_type = COLOR_TYPE_MAP.get(color_type, f"unknown({color_type})")

    def _parse_gamma(self, chunk_data: bytes) -> float:
        if len(chunk_data) != 4:
            raise PNGChunkParserError("gAMA chunk length is invalid.")
        (gamma_value,) = struct.unpack(">I", chunk_data)
        return gamma_value / 100000

    def _parse_iccp(self, chunk_data: bytes) -> str:
        if b"\x00" not in chunk_data:
            return "ICC profile present"
        keyword, remainder = chunk_data.split(b"\x00", 1)
        keyword_text = keyword.decode("latin-1", errors="replace")
        if len(remainder) < 2:
            return f"ICC profile present ({keyword_text})"
        compressed = remainder[1:]
        return f"ICC profile present ({keyword_text}, {len(compressed)} bytes compressed)"

    def _parse_text_chunk(self, chunk_name: str, chunk_data: bytes, text_budget: int) -> dict[str, str] | None:
        if chunk_name == "tEXt":
            if b"\x00" not in chunk_data:
                return None
            keyword, value = chunk_data.split(b"\x00", 1)
            return {
                "type": chunk_name,
                "key": keyword.decode("latin-1", errors="replace"),
                "value": value.decode("latin-1", errors="replace")[:text_budget],
            }

        if chunk_name == "zTXt":
            if b"\x00" not in chunk_data:
                return None
            keyword, remainder = chunk_data.split(b"\x00", 1)
            if len(remainder) < 2:
                return None
            compression_method = remainder[0:1]
            if compression_method != b"\x00":
                return None
            compressed_text = remainder[1:]
            value = self._safe_decompress(compressed_text, text_budget).decode("latin-1", errors="replace")
            return {
                "type": chunk_name,
                "key": keyword.decode("latin-1", errors="replace"),
                "value": value,
            }

        if b"\x00" not in chunk_data:
            return None
        keyword, remainder = chunk_data.split(b"\x00", 1)
        if len(remainder) < 2:
            return None
        compression_flag = remainder[0:1]
        compression_method = remainder[1:2]
        if compression_flag not in {b"\x00", b"\x01"}:
            return None
        if compression_method != b"\x00":
            return None

        remainder = remainder[2:]
        if b"\x00" not in remainder:
            return None
        language_tag, remainder = remainder.split(b"\x00", 1)
        if b"\x00" not in remainder:
            return None
        translated_keyword, text_data = remainder.split(b"\x00", 1)
        if compression_flag == b"\x01":
            decoded_text = self._safe_decompress(text_data, text_budget).decode("utf-8", errors="replace")
        else:
            decoded_text = text_data.decode("utf-8", errors="replace")
        return {
            "type": chunk_name,
            "key": keyword.decode("latin-1", errors="replace"),
            "value": decoded_text[:text_budget],
            "language": language_tag.decode("ascii", errors="replace"),
            "translated_key": translated_keyword.decode("utf-8", errors="replace"),
        }

    def _safe_decompress(self, payload: bytes, limit: int) -> bytes:
        decompressor = zlib.decompressobj()
        result = decompressor.decompress(payload, limit)
        if decompressor.unconsumed_tail:
            result += decompressor.flush(limit - len(result))
        return result[:limit]
