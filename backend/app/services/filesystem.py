from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterator

from app.core.config import Settings


class PathValidationError(ValueError):
    """Raised when a relative path is invalid or escapes the configured root."""


@dataclass(slots=True)
class DiscoveredFile:
    relative_path: str
    absolute_path: Path
    stat_result: os.stat_result


class FileSystemService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root_path = Path(settings.png_root_dir).expanduser()
        self.thumbnail_cache_path = Path(settings.thumbnail_cache_dir).expanduser()

    def ensure_roots(self) -> None:
        self.thumbnail_cache_path.mkdir(parents=True, exist_ok=True)
        if not self.root_path.exists():
            raise FileNotFoundError(f"PNG_ROOT_DIR does not exist: {self.root_path}")
        if not self.root_path.is_dir():
            raise NotADirectoryError(f"PNG_ROOT_DIR is not a directory: {self.root_path}")
        self.root_path = self.root_path.resolve(strict=True)
        self.thumbnail_cache_path = self.thumbnail_cache_path.resolve(strict=True)

    def normalize_relative_path(self, relative_path: str | None) -> str:
        if relative_path is None:
            return ""
        cleaned = relative_path.strip().replace("\\", "/")
        if cleaned in {"", ".", "/"}:
            return ""
        parsed = PurePosixPath(cleaned)
        if parsed.is_absolute():
            raise PathValidationError("Absolute paths are not allowed.")

        parts = [part for part in parsed.parts if part not in {"", "."}]
        if any(part == ".." for part in parts):
            raise PathValidationError("Path traversal is not allowed.")
        if any(":" in part for part in parts):
            raise PathValidationError("Drive-qualified paths are not allowed.")

        normalized = "/".join(parts)
        if normalized.startswith("../") or normalized == "..":
            raise PathValidationError("Path traversal is not allowed.")
        return normalized

    def resolve_relative_path(self, relative_path: str, *, strict: bool = True) -> Path:
        normalized = self.normalize_relative_path(relative_path)
        candidate = self.root_path.joinpath(*PurePosixPath(normalized).parts)

        if strict:
            if not candidate.exists():
                raise FileNotFoundError(normalized)
            resolved = candidate.resolve(strict=True)
        else:
            resolved = candidate.resolve(strict=False)

        if not self._is_within_root(resolved):
            raise PathValidationError("Requested path escapes PNG_ROOT_DIR.")
        if not self.settings.allow_symlinks and self._contains_symlink(candidate):
            raise PathValidationError("Symlink traversal is disabled.")
        return resolved

    def _contains_symlink(self, candidate: Path) -> bool:
        current = self.root_path
        try:
            relative = candidate.relative_to(self.root_path)
        except ValueError:
            return True

        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                return True
        return False

    def _is_within_root(self, path: Path) -> bool:
        try:
            path.relative_to(self.root_path)
            return True
        except ValueError:
            return False

    def iter_png_files(self) -> Iterator[DiscoveredFile]:
        yield from self._iter_directory(self.root_path, "")

    def _iter_directory(self, current_path: Path, relative_dir: str) -> Iterator[DiscoveredFile]:
        entries = sorted(os.scandir(current_path), key=lambda entry: (not entry.is_dir(follow_symlinks=False), entry.name.lower()))
        for entry in entries:
            entry_path = Path(entry.path)
            relative_path = f"{relative_dir}/{entry.name}" if relative_dir else entry.name
            normalized_relative = relative_path.replace("\\", "/")

            if entry.is_symlink():
                if not self.settings.allow_symlinks:
                    continue
                try:
                    resolved_symlink = entry_path.resolve(strict=True)
                except FileNotFoundError:
                    continue
                if not self._is_within_root(resolved_symlink):
                    continue

            if entry.is_dir(follow_symlinks=self.settings.allow_symlinks):
                try:
                    resolved_dir = entry_path.resolve(strict=True)
                except FileNotFoundError:
                    continue
                if not self._is_within_root(resolved_dir):
                    continue
                yield from self._iter_directory(entry_path, normalized_relative)
                continue

            if not entry.is_file(follow_symlinks=self.settings.allow_symlinks):
                continue
            if not entry.name.lower().endswith(".png"):
                continue

            try:
                resolved_file = entry_path.resolve(strict=True)
            except FileNotFoundError:
                continue
            if not self._is_within_root(resolved_file):
                continue
            if not self.settings.allow_symlinks and self._contains_symlink(entry_path):
                continue

            stat_result = os.stat(entry.path, follow_symlinks=self.settings.allow_symlinks)
            yield DiscoveredFile(
                relative_path=normalized_relative,
                absolute_path=entry_path,
                stat_result=stat_result,
            )

