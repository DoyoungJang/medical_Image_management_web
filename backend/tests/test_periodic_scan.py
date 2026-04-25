from __future__ import annotations

import time

from app.core.config import Settings
from app.services.periodic_scan import PeriodicScanService


class _FakeIndexService:
    def __init__(self) -> None:
        self.reasons: list[str] = []

    def trigger_background_scan(self, *, reason: str) -> bool:
        self.reasons.append(reason)
        return True


def test_periodic_scan_triggers_background_scan() -> None:
    index_service = _FakeIndexService()
    service = PeriodicScanService(
        Settings(periodic_scan_interval_seconds=1),
        index_service,  # type: ignore[arg-type]
    )

    service.start()
    try:
        deadline = time.monotonic() + 2.5
        while time.monotonic() < deadline and not index_service.reasons:
            time.sleep(0.05)
    finally:
        service.stop()

    assert "periodic" in index_service.reasons


def test_periodic_scan_can_be_disabled() -> None:
    index_service = _FakeIndexService()
    service = PeriodicScanService(
        Settings(periodic_scan_interval_seconds=0),
        index_service,  # type: ignore[arg-type]
    )

    service.start()
    time.sleep(0.1)
    service.stop()

    assert index_service.reasons == []
