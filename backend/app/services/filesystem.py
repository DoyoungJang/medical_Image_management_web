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


@dataclass(slots=True)
class DiscoveredDirectory:
    relative_path: str
    absolute_path: Path


class FileSystemService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root_path = Path(settings.png_root_dir).expanduser()
        self.thumbnail_cache_path = Path(settings.thumbnail_cache_dir).expanduser()
        self.supported_extensions = {extension.lower() for extension in settings.supported_image_extensions}

    def ensure_roots(self) -> None:
        self.thumbnail_cache_path.mkdir(parents=True, exist_ok=True)
        self.thumbnail_cache_path = self.thumbnail_cache_path.resolve(strict=True)
        self.root_path = self.validate_root_path(str(self.root_path))
        self.settings.png_root_dir = str(self.root_path)

    def set_root_path(self, root_dir: str) -> Path:
        self.root_path = Path(root_dir).expanduser()
        self.ensure_roots()
        return self.root_path

    def validate_root_path(self, root_dir: str) -> Path:
        cleaned = root_dir.strip()
        if not cleaned:
            raise ValueError("이미지 루트 경로를 입력하세요.")

        root_path = Path(cleaned).expanduser()
        if not root_path.exists():
            raise FileNotFoundError(f"PNG_ROOT_DIR가 존재하지 않습니다: {root_path}")
        if not root_path.is_dir():
            raise NotADirectoryError(f"PNG_ROOT_DIR가 디렉터리가 아닙니다: {root_path}")

        resolved_root = root_path.resolve(strict=True)
        self._ensure_thumbnail_cache_outside_root(resolved_root)
        return resolved_root

    def _ensure_thumbnail_cache_outside_root(self, resolved_root: Path) -> None:
        try:
            self.thumbnail_cache_path.relative_to(resolved_root)
        except ValueError:
            return
        raise ValueError("THUMBNAIL_CACHE_DIR는 이미지 루트 경로 밖에 있어야 합니다.")

    def normalize_relative_path(self, relative_path: str | None) -> str:
        if relative_path is None:
            return ""
        cleaned = relative_path.strip().replace("\\", "/")
        if cleaned in {"", ".", "/"}:
            return ""
        parsed = PurePosixPath(cleaned)
        if parsed.is_absolute():
            raise PathValidationError("절대 경로는 사용할 수 없습니다.")

        parts = [part for part in parsed.parts if part not in {"", "."}]
        if any(part == ".." for part in parts):
            raise PathValidationError("상위 경로 이동은 허용되지 않습니다.")
        if any(":" in part for part in parts):
            raise PathValidationError("드라이브가 포함된 경로는 사용할 수 없습니다.")

        normalized = "/".join(parts)
        if normalized.startswith("../") or normalized == "..":
            raise PathValidationError("상위 경로 이동은 허용되지 않습니다.")
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
            raise PathValidationError("요청한 경로가 PNG_ROOT_DIR 밖으로 벗어납니다.")
        if not self.settings.allow_symlinks and self._contains_symlink(candidate):
            raise PathValidationError("심볼릭 링크 탐색은 비활성화되어 있습니다.")
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

    def iter_image_files(self) -> Iterator[DiscoveredFile]:
        yield from self._iter_directory(self.root_path, "")

    def iter_png_files(self) -> Iterator[DiscoveredFile]:
        yield from self.iter_image_files()

    def iter_directories(self) -> Iterator[DiscoveredDirectory]:
        yield DiscoveredDirectory(relative_path="", absolute_path=self.root_path)
        yield from self._iter_directories(self.root_path, "", {self.root_path})

    def _iter_directories(
        self,
        current_path: Path,
        relative_dir: str,
        visited: set[Path],
    ) -> Iterator[DiscoveredDirectory]:
        entries = sorted(os.scandir(current_path), key=lambda entry: entry.name.lower())
        for entry in entries:
            if entry.is_symlink() and not self.settings.allow_symlinks:
                continue
            if not entry.is_dir(follow_symlinks=self.settings.allow_symlinks):
                continue

            entry_path = Path(entry.path)
            relative_path = f"{relative_dir}/{entry.name}" if relative_dir else entry.name
            normalized_relative = relative_path.replace("\\", "/")

            try:
                resolved_dir = entry_path.resolve(strict=True)
            except FileNotFoundError:
                continue
            if not self._is_within_root(resolved_dir):
                continue
            if resolved_dir in visited:
                continue

            visited.add(resolved_dir)
            yield DiscoveredDirectory(relative_path=normalized_relative, absolute_path=entry_path)
            yield from self._iter_directories(entry_path, normalized_relative, visited)

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
            if Path(entry.name).suffix.lower() not in self.supported_extensions:
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
