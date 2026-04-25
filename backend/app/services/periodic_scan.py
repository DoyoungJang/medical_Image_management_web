from __future__ import annotations

import threading

from app.core.config import Settings
from app.services.indexing import IndexService


class PeriodicScanService:
    def __init__(self, settings: Settings, index_service: IndexService) -> None:
        self.settings = settings
        self.index_service = index_service
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        interval_seconds = self.settings.periodic_scan_interval_seconds
        if interval_seconds <= 0:
            return
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="periodic-png-rescan", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join(timeout=5)
        self._thread = None

    def _run(self) -> None:
        interval_seconds = self.settings.periodic_scan_interval_seconds
        while not self._stop_event.wait(interval_seconds):
            self.index_service.trigger_background_scan(reason="periodic")
