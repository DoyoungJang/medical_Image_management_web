from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.models import Image
from app.services.filesystem import FileSystemService, PathValidationError
from app.services.object_storage import ObjectStorageError, ObjectStorageService
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
        object_storage_service: ObjectStorageService,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.file_system_service = file_system_service
        self.search_service = search_service
        self.object_storage_service = object_storage_service
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
        raise ValueError("EXPORT_ROOT_DIR must be outside the image root path.")

    def export_filtered_images(
        self,
        filters: SearchFilters,
        destination_dir: str,
        *,
        structure_mode: str = "preserve",
        image_ids: list[int] | None = None,
        storage_backend: str | None = None,
    ) -> ExportResult:
        normalized_destination = self._normalize_destination(destination_dir)
        normalized_structure_mode = self._normalize_structure_mode(structure_mode)
        normalized_storage_backend = self._normalize_storage_backend(storage_backend)

        resolved_destination: Path | None = None
        if normalized_storage_backend == "local":
            destination_root = self.export_root_path.joinpath(*PurePosixPath(normalized_destination).parts)
            destination_root.mkdir(parents=True, exist_ok=True)
            resolved_destination = destination_root.resolve(strict=True)
            if not self._is_within_export_root(resolved_destination):
                raise PathValidationError("Export destination escaped the configured export root.")

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
                if self._export_image(
                    image,
                    normalized_destination,
                    resolved_destination,
                    normalized_structure_mode,
                    normalized_storage_backend,
                    used_flat_names,
                ):
                    copied += 1
                else:
                    skipped += 1

        destination_label = normalized_destination
        if normalized_storage_backend == "object":
            object_prefix = self.object_storage_service.normalize_object_key(normalized_destination)
            destination_label = f"s3://{self.settings.object_storage_bucket}/{object_prefix}"

        return ExportResult(
            destination_dir=destination_label,
            copied=copied,
            skipped=skipped,
            total_matched=total_matched,
            limit_applied=total_matched > len(images),
        )

    def _export_image(
        self,
        image: Image,
        normalized_destination: str,
        destination_root: Path | None,
        structure_mode: str,
        storage_backend: str,
        used_flat_names: set[str],
    ) -> bool:
        try:
            source_path = self.file_system_service.resolve_relative_path(image.relative_path, strict=True)
        except (FileNotFoundError, PathValidationError):
            return False

        target_relative_path = self._target_relative_path(image, structure_mode, used_flat_names)
        if storage_backend == "object":
            object_key = f"{normalized_destination}/{target_relative_path}"
            self.object_storage_service.upload_file(source_path, object_key, filename=image.filename)
            return True

        if destination_root is None:
            return False
        target_path = destination_root.joinpath(*PurePosixPath(target_relative_path).parts)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_target_parent = target_path.parent.resolve(strict=True)
        if not self._is_within_export_root(resolved_target_parent):
            return False
        shutil.copy2(source_path, target_path)
        return True

    def _target_relative_path(self, image: Image, structure_mode: str, used_flat_names: set[str]) -> str:
        if structure_mode == "flat":
            return self._unique_flat_filename(image.filename, used_flat_names)
        return image.relative_path

    def _normalize_destination(self, destination_dir: str) -> str:
        cleaned = destination_dir.strip().replace("\\", "/")
        if not cleaned:
            raise PathValidationError("Destination folder name is required.")
        parsed = PurePosixPath(cleaned)
        if parsed.is_absolute():
            raise PathValidationError("Absolute paths are not allowed for export destinations.")
        parts = [part for part in parsed.parts if part not in {"", "."}]
        if any(part == ".." for part in parts):
            raise PathValidationError("Parent-directory traversal is not allowed.")
        if any(":" in part for part in parts):
            raise PathValidationError("Drive-qualified paths are not allowed.")
        return "/".join(parts)

    def _normalize_structure_mode(self, structure_mode: str) -> str:
        normalized = structure_mode.strip().lower()
        if normalized not in {"preserve", "flat"}:
            raise PathValidationError("structure_mode must be preserve or flat.")
        return normalized

    def _normalize_storage_backend(self, storage_backend: str | None) -> str:
        normalized = (storage_backend or self.settings.export_storage_backend).strip().lower()
        if normalized not in {"local", "object"}:
            raise PathValidationError("storage_backend must be local or object.")
        if normalized == "object" and not self.object_storage_service.is_configured():
            raise ObjectStorageError("Object storage export is not configured.")
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
