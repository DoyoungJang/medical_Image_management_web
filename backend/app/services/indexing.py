from __future__ import annotations

import hashlib
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.core.config import Settings
from app.models import Image, MetadataKV
from app.services.filesystem import DiscoveredFile, FileSystemService
from app.services.metadata import ExtractedMetadata, MetadataExtractor
from app.services.search import SearchService


@dataclass(slots=True)
class ScanResult:
    reason: str
    scanned: int
    updated: int
    skipped: int
    missing_marked: int
    errors: int


class IndexService:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: sessionmaker[Session],
        file_system_service: FileSystemService,
        metadata_extractor: MetadataExtractor,
        search_service: SearchService,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.file_system_service = file_system_service
        self.metadata_extractor = metadata_extractor
        self.search_service = search_service

        self._scan_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._scanning = False
        self._last_started_at: datetime | None = None
        self._last_finished_at: datetime | None = None
        self._last_result: dict[str, object] | None = None

    def trigger_background_scan(self, *, reason: str) -> bool:
        with self._state_lock:
            if self._scanning:
                return False
            now = datetime.now(tz=timezone.utc)
            if (
                reason == "manual"
                and self._last_started_at is not None
                and (now - self._last_started_at).total_seconds() < self.settings.admin_rescan_cooldown_seconds
            ):
                return False
            self._scanning = True
            self._last_started_at = now

        thread = threading.Thread(target=self._run_scan, kwargs={"reason": reason}, daemon=True)
        thread.start()
        return True

    def is_scanning(self) -> bool:
        with self._state_lock:
            return self._scanning

    def scan_now(self, *, reason: str) -> ScanResult:
        with self._state_lock:
            self._scanning = True
            self._last_started_at = datetime.now(tz=timezone.utc)
        return self._execute_scan(reason=reason)

    def _run_scan(self, *, reason: str) -> None:
        self._execute_scan(reason=reason)

    def _execute_scan(self, *, reason: str) -> ScanResult:
        with self._scan_lock:
            result = ScanResult(reason=reason, scanned=0, updated=0, skipped=0, missing_marked=0, errors=0)
            finished_at = datetime.now(tz=timezone.utc)
            try:
                with self.session_factory() as session:
                    existing_images = {
                        image.relative_path: image
                        for image in session.execute(
                            select(Image).options(selectinload(Image.metadata_entries))
                        ).scalars()
                    }

                    discovered_directories = {
                        discovered.relative_path for discovered in self.file_system_service.iter_directories()
                    }
                    seen_paths: set[str] = set()
                    for discovered in self.file_system_service.iter_image_files():
                        seen_paths.add(discovered.relative_path)
                        result.scanned += 1
                        current_image = existing_images.get(discovered.relative_path)
                        modified_time = datetime.fromtimestamp(discovered.stat_result.st_mtime, tz=timezone.utc)
                        content_hash = self._hash_file(discovered.absolute_path)

                        if current_image is not None and self._is_unchanged(current_image, discovered, modified_time, content_hash):
                            result.skipped += 1
                            continue

                        extracted = self.metadata_extractor.extract(
                            discovered.absolute_path,
                            discovered.relative_path,
                            discovered.stat_result,
                            content_hash=content_hash,
                        )
                        self._upsert_image(session, current_image, extracted)
                        result.updated += 1
                        if extracted.status != "ok":
                            result.errors += 1

                    finished_at = datetime.now(tz=timezone.utc)
                    for relative_path, image in existing_images.items():
                        if relative_path in seen_paths or image.missing_at is not None:
                            continue
                        image.missing_at = finished_at
                        image.status = "missing"
                        image.indexed_at = finished_at
                        result.missing_marked += 1

                    session.flush()
                    self.search_service.rebuild_search_indexes(
                        session,
                        indexed_at=finished_at,
                        folder_paths=discovered_directories,
                    )
                    session.commit()
            finally:
                with self._state_lock:
                    self._scanning = False
                    self._last_finished_at = finished_at
                    self._last_result = asdict(result)
            return result

    def _upsert_image(self, session: Session, current_image: Image | None, extracted: ExtractedMetadata) -> Image:
        now = datetime.now(tz=timezone.utc)
        image = current_image or Image(relative_path=extracted.relative_path)
        if current_image is None:
            session.add(image)

        image.filename = extracted.filename
        image.directory = extracted.directory
        image.extension = extracted.extension
        image.file_size_bytes = extracted.file_size_bytes
        image.content_hash = extracted.content_hash
        image.modified_time = extracted.modified_time
        image.width = extracted.width
        image.height = extracted.height
        image.format = extracted.format
        image.mode = extracted.mode
        image.bit_depth = extracted.bit_depth
        image.color_type = extracted.color_type
        image.has_alpha = extracted.has_alpha
        image.dpi_x = extracted.dpi_x
        image.dpi_y = extracted.dpi_y
        image.metadata_json = self.metadata_extractor.serialize_metadata(extracted.metadata)
        image.metadata_text = extracted.metadata_text
        image.status = extracted.status
        image.error_message = extracted.error_message
        image.indexed_at = now
        image.missing_at = None

        image.metadata_entries.clear()
        image.metadata_entries.extend(
            MetadataKV(
                key=pair.key,
                value_text=pair.value_text,
                value_number=pair.value_number,
            )
            for pair in extracted.metadata_pairs
        )
        return image

    def _is_unchanged(self, image: Image, discovered: DiscoveredFile, modified_time: datetime, content_hash: str) -> bool:
        if image.missing_at is not None:
            return False
        if image.file_size_bytes != int(discovered.stat_result.st_size):
            return False
        if image.content_hash is None:
            # Existing databases need one refresh to store hashes before hash-based skipping is safe.
            return False
        if image.content_hash != content_hash:
            return False

        stored_modified_time = image.modified_time
        if stored_modified_time.tzinfo is None:
            # SQLite returns naive datetimes even when SQLAlchemy is configured with timezone=True.
            stored_modified_time = stored_modified_time.replace(tzinfo=timezone.utc)
        return abs(stored_modified_time.timestamp() - modified_time.timestamp()) < 0.001

    def _hash_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def mark_all_active_missing(self) -> int:
        indexed_at = datetime.now(tz=timezone.utc)
        with self.session_factory() as session:
            result = session.execute(
                update(Image)
                .where(Image.missing_at.is_(None))
                .values(missing_at=indexed_at, status="missing", indexed_at=indexed_at)
            )
            self.search_service.rebuild_search_indexes(session, indexed_at=indexed_at, folder_paths={""})
            session.commit()
            return int(result.rowcount or 0)

    def get_status(self, session: Session) -> dict[str, object]:
        counts = self.search_service.get_index_counts(session)
        with self._state_lock:
            return {
                "scanning": self._scanning,
                "last_started_at": self._last_started_at,
                "last_finished_at": self._last_finished_at,
                "last_result": self._last_result,
                **counts,
            }
