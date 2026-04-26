from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.models import Image as ImageModel
from app.services.filesystem import FileSystemService


class ThumbnailError(RuntimeError):
    """Raised when a thumbnail cannot be generated."""


class ThumbnailService:
    def __init__(
        self,
        settings: Settings,
        file_system_service: FileSystemService,
        session_factory: sessionmaker[Session],
    ) -> None:
        self.settings = settings
        self.file_system_service = file_system_service
        self.session_factory = session_factory

    def get_thumbnail_path(self, image: ImageModel, size: int) -> Path:
        bounded_size = min(max(size, 32), self.settings.thumbnail_max_size)
        source_path = self.file_system_service.resolve_relative_path(image.relative_path, strict=True)
        source_identity = image.content_hash or image.modified_time.isoformat()
        cache_key = hashlib.sha256(
            f"{image.relative_path}|{source_identity}|{bounded_size}".encode("utf-8")
        ).hexdigest()
        cache_dir = self.file_system_service.thumbnail_cache_path / cache_key[:2]
        cache_dir.mkdir(parents=True, exist_ok=True)
        thumbnail_path = cache_dir / f"{cache_key}.png"
        if thumbnail_path.exists():
            return thumbnail_path

        try:
            with Image.open(source_path) as source_image:
                source_image.load()
                preview = source_image.copy()
                preview.thumbnail((bounded_size, bounded_size), Image.Resampling.LANCZOS)
                if preview.mode not in {"1", "L", "LA", "P", "RGB", "RGBA"}:
                    preview = preview.convert("RGB")
                preview.save(thumbnail_path, format="PNG", optimize=True)
        except (UnidentifiedImageError, OSError) as exc:
            raise ThumbnailError("이 이미지 파일의 썸네일을 생성할 수 없습니다.") from exc

        return thumbnail_path
