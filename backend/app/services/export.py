from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.models import Image
from app.services.filesystem import FileSystemService, PathValidationError
from app.services.search import SearchFilters, SearchService


@dataclass(frozen=True, slots=True)
class ExportResult:
    destination_dir: str
    copied: int
    skipped: int
    total_matched: int
    limit_applied: bool


class ExportService:
    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        file_system_service: FileSystemService,
        search_service: SearchService,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.file_system_service = file_system_service
        self.search_service = search_service
        self.export_root_path = Path(settings.export_root_dir).expanduser()

    def set_export_root_path(self, root_dir: str) -> Path:
        self.export_root_path = Path(root_dir.strip()).expanduser()
        self.ensure_export_root()
        self.settings.export_root_dir = str(self.export_root_path)
        return self.export_root_path

    def ensure_export_root(self) -> None:
        self.export_root_path.mkdir(parents=True, exist_ok=True)
        self.export_root_path = self.export_root_path.resolve(strict=True)
        try:
            self.export_root_path.relative_to(self.file_system_service.root_path)
        except ValueError:
            return
        raise ValueError("EXPORT_ROOT_DIR는 이미지 루트 경로 밖에 있어야 합니다.")

    def export_filtered_images(
        self,
        filters: SearchFilters,
        destination_dir: str,
        *,
        structure_mode: str = "preserve",
        image_ids: list[int] | None = None,
    ) -> ExportResult:
        normalized_destination = self._normalize_destination(destination_dir)
        normalized_structure_mode = self._normalize_structure_mode(structure_mode)
        destination_root = self.export_root_path.joinpath(*PurePosixPath(normalized_destination).parts)
        destination_root.mkdir(parents=True, exist_ok=True)
        resolved_destination = destination_root.resolve(strict=True)
        if not self._is_within_export_root(resolved_destination):
            raise PathValidationError("내보내기 대상이 EXPORT_ROOT_DIR 밖으로 벗어납니다.")

        copied = 0
        skipped = 0
        with self.session_factory() as session:
            if image_ids:
                images = self.search_service.get_images_by_ids(session, image_ids, limit=self.settings.max_export_items)
                total_matched = len(set(image_ids))
            else:
                total_matched = self.search_service.count_images(session, filters)
                images = self.search_service.search_all_images(session, filters, limit=self.settings.max_export_items)
            used_flat_names: set[str] = set()
            for image in images:
                if self._copy_image(image, resolved_destination, normalized_structure_mode, used_flat_names):
                    copied += 1
                else:
                    skipped += 1

        return ExportResult(
            destination_dir=normalized_destination,
            copied=copied,
            skipped=skipped,
            total_matched=total_matched,
            limit_applied=total_matched > len(images),
        )

    def _copy_image(
        self,
        image: Image,
        destination_root: Path,
        structure_mode: str,
        used_flat_names: set[str],
    ) -> bool:
        try:
            source_path = self.file_system_service.resolve_relative_path(image.relative_path, strict=True)
        except (FileNotFoundError, PathValidationError):
            return False

        if structure_mode == "flat":
            target_path = destination_root / self._unique_flat_filename(image.filename, used_flat_names)
        else:
            relative_parts = PurePosixPath(image.relative_path).parts
            target_path = destination_root.joinpath(*relative_parts)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_target_parent = target_path.parent.resolve(strict=True)
        if not self._is_within_export_root(resolved_target_parent):
            return False
        shutil.copy2(source_path, target_path)
        return True

    def _normalize_destination(self, destination_dir: str) -> str:
        cleaned = destination_dir.strip().replace("\\", "/")
        if not cleaned:
            raise PathValidationError("저장할 폴더명을 입력하세요.")
        parsed = PurePosixPath(cleaned)
        if parsed.is_absolute():
            raise PathValidationError("내보내기 대상에는 절대 경로를 사용할 수 없습니다.")
        parts = [part for part in parsed.parts if part not in {"", "."}]
        if any(part == ".." for part in parts):
            raise PathValidationError("상위 경로 이동은 허용되지 않습니다.")
        if any(":" in part for part in parts):
            raise PathValidationError("드라이브가 포함된 경로는 사용할 수 없습니다.")
        return "/".join(parts)

    def _normalize_structure_mode(self, structure_mode: str) -> str:
        normalized = structure_mode.strip().lower()
        if normalized not in {"preserve", "flat"}:
            raise PathValidationError("structure_mode must be preserve or flat.")
        return normalized

    def _unique_flat_filename(self, filename: str, used_names: set[str]) -> str:
        source = Path(filename)
        stem = source.stem or "image"
        suffix = source.suffix
        candidate = filename
        index = 2
        while candidate.lower() in used_names:
            candidate = f"{stem}_{index}{suffix}"
            index += 1
        used_names.add(candidate.lower())
        return candidate

    def _is_within_export_root(self, path: Path) -> bool:
        try:
            path.relative_to(self.export_root_path)
            return True
        except ValueError:
            return False
