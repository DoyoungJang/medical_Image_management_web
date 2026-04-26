from __future__ import annotations

import threading

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db import Base, create_db_engine, create_session_factory, ensure_schema_compatibility
from app.schemas import AdminImageRootResponse
from app.services.auth import AuthService
from app.services.export import ExportService
from app.services.filesystem import FileSystemService
from app.services.indexing import IndexService
from app.services.metadata import MetadataExtractor
from app.services.periodic_scan import PeriodicScanService
from app.services.runtime_config import RuntimeConfigService
from app.services.search import SearchService
from app.services.thumbnails import ThumbnailService
from app.services.watch import WatchService


class RootPathUpdateError(RuntimeError):
    """Raised when the image root cannot be updated safely at runtime."""


class AppContainer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.env_png_root_dir = settings.png_root_dir
        self.engine = create_db_engine(settings)
        self.session_factory: sessionmaker[Session] = create_session_factory(self.engine)
        self.runtime_config_service = RuntimeConfigService(
            self.session_factory,
            env_root_dir=self.env_png_root_dir,
        )
        self._root_update_lock = threading.Lock()

        self.file_system_service = FileSystemService(settings)
        self.metadata_extractor = MetadataExtractor(settings)
        self.search_service = SearchService(settings, self.session_factory)
        self.thumbnail_service = ThumbnailService(settings, self.file_system_service, self.session_factory)
        self.export_service = ExportService(
            settings,
            self.session_factory,
            self.file_system_service,
            self.search_service,
        )
        self.index_service = IndexService(
            settings=settings,
            session_factory=self.session_factory,
            file_system_service=self.file_system_service,
            metadata_extractor=self.metadata_extractor,
            search_service=self.search_service,
        )
        self.auth_service = AuthService(settings)
        self.watch_service = WatchService(settings, self.index_service)
        self.periodic_scan_service = PeriodicScanService(settings, self.index_service)

    def initialize(self) -> None:
        Base.metadata.create_all(bind=self.engine)
        ensure_schema_compatibility(self.engine)
        runtime_root_config = self.runtime_config_service.get_image_root_config()
        self.file_system_service.set_root_path(runtime_root_config.root_dir)
        self.export_service.ensure_export_root()
        self.search_service.initialize()

    def start_background_services(self) -> None:
        if self.settings.auto_scan_on_startup:
            self.index_service.trigger_background_scan(reason="startup")
        self.periodic_scan_service.start()
        if self.settings.enable_watchdog:
            self.watch_service.start(self.file_system_service.root_path)

    def stop_background_services(self) -> None:
        self.periodic_scan_service.stop()
        self.watch_service.stop()

    def get_image_root_config(self) -> AdminImageRootResponse:
        runtime_config = self.runtime_config_service.get_image_root_config()
        return AdminImageRootResponse(
            root_dir=str(self.file_system_service.root_path),
            env_root_dir=runtime_config.env_root_dir,
            source=runtime_config.source,
            changed=False,
            rescan_accepted=None,
            missing_marked=0,
        )

    def update_image_root(self, root_dir: str, *, rescan: bool = True) -> AdminImageRootResponse:
        with self._root_update_lock:
            if self.index_service.is_scanning():
                raise RootPathUpdateError("스캔이 진행 중일 때는 이미지 루트 경로를 변경할 수 없습니다.")

            previous_root = self.file_system_service.root_path
            resolved_root = self.file_system_service.validate_root_path(root_dir)
            changed = resolved_root != previous_root

            runtime_config = self.runtime_config_service.set_image_root_dir(str(resolved_root))
            self.watch_service.stop()
            self.file_system_service.set_root_path(str(resolved_root))
            self.export_service.ensure_export_root()

            missing_marked = self.index_service.mark_all_active_missing() if changed else 0
            if self.settings.enable_watchdog:
                self.watch_service.start(self.file_system_service.root_path)

            rescan_accepted = False
            if rescan:
                rescan_accepted = self.index_service.trigger_background_scan(reason="root-change")

            return AdminImageRootResponse(
                root_dir=str(self.file_system_service.root_path),
                env_root_dir=runtime_config.env_root_dir,
                source=runtime_config.source,
                changed=changed,
                rescan_accepted=rescan_accepted,
                missing_marked=missing_marked,
            )
