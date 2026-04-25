from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db import Base, create_db_engine, create_session_factory, ensure_schema_compatibility
from app.services.auth import AuthService
from app.services.filesystem import FileSystemService
from app.services.indexing import IndexService
from app.services.metadata import MetadataExtractor
from app.services.periodic_scan import PeriodicScanService
from app.services.search import SearchService
from app.services.thumbnails import ThumbnailService
from app.services.watch import WatchService


class AppContainer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = create_db_engine(settings)
        self.session_factory: sessionmaker[Session] = create_session_factory(self.engine)

        self.file_system_service = FileSystemService(settings)
        self.metadata_extractor = MetadataExtractor(settings)
        self.search_service = SearchService(settings, self.session_factory)
        self.thumbnail_service = ThumbnailService(settings, self.file_system_service, self.session_factory)
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
        self.file_system_service.ensure_roots()
        Base.metadata.create_all(bind=self.engine)
        ensure_schema_compatibility(self.engine)
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
