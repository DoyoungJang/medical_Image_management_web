from __future__ import annotations

import threading
from pathlib import Path

from app.core.config import Settings
from app.services.indexing import IndexService

try:  # pragma: no cover - optional dependency exercised in production only
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except Exception:  # pragma: no cover - handled gracefully below
    FileSystemEventHandler = object  # type: ignore[assignment]
    Observer = None  # type: ignore[assignment]


class _RescanEventHandler(FileSystemEventHandler):  # pragma: no cover - event-driven helper
    def __init__(self, index_service: IndexService) -> None:
        self.index_service = index_service
        self._timer: threading.Timer | None = None

    def on_any_event(self, event) -> None:
        if self._timer is not None:
            self._timer.cancel()
        self._timer = threading.Timer(1.0, lambda: self.index_service.trigger_background_scan(reason="watchdog"))
        self._timer.daemon = True
        self._timer.start()


class WatchService:
    def __init__(self, settings: Settings, index_service: IndexService) -> None:
        self.settings = settings
        self.index_service = index_service
        self._observer = None

    def start(self, root_path: Path) -> None:
        if not self.settings.enable_watchdog or Observer is None:
            return
        if self._observer is not None:
            return
        self._observer = Observer()
        self._observer.schedule(_RescanEventHandler(self.index_service), str(root_path), recursive=True)
        self._observer.daemon = True
        self._observer.start()

    def stop(self) -> None:
        if self._observer is None:
            return
        self._observer.stop()
        self._observer.join(timeout=5)
        self._observer = None
