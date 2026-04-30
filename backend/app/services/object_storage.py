from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from app.core.config import Settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class ObjectStorageError(RuntimeError):
    """Raised when object storage export is not configured or upload fails."""


@dataclass(frozen=True, slots=True)
class ObjectDestination:
    bucket: str
    key: str


class ObjectStorageService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: S3Client | None = None

    def is_configured(self) -> bool:
        return bool(
            self.settings.object_storage_endpoint_url
            and self.settings.object_storage_access_key_id
            and self.settings.object_storage_secret_access_key
            and self.settings.object_storage_bucket
        )

    def upload_file(self, source_path: Path, object_key: str, *, filename: str) -> ObjectDestination:
        self._ensure_configured()
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        key = self.normalize_object_key(object_key)
        try:
            self._client_instance().upload_file(
                str(source_path),
                self.settings.object_storage_bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
        except Exception as exc:
            raise ObjectStorageError(f"Object storage upload failed: {key}") from exc
        return ObjectDestination(bucket=self.settings.object_storage_bucket, key=key)

    def _ensure_configured(self) -> None:
        if not self.is_configured():
            raise ObjectStorageError(
                "Object storage export is not configured. Set OBJECT_STORAGE_ENDPOINT_URL, "
                "OBJECT_STORAGE_ACCESS_KEY_ID, OBJECT_STORAGE_SECRET_ACCESS_KEY, and OBJECT_STORAGE_BUCKET."
            )

    def _client_instance(self) -> S3Client:
        if self._client is not None:
            return self._client

        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise ObjectStorageError("boto3 is required for MinIO/lakeFS object storage export.") from exc

        addressing_style = "path" if self.settings.object_storage_force_path_style else "auto"
        self._client = boto3.client(
            "s3",
            endpoint_url=self.settings.object_storage_endpoint_url,
            aws_access_key_id=self.settings.object_storage_access_key_id,
            aws_secret_access_key=self.settings.object_storage_secret_access_key,
            region_name=self.settings.object_storage_region,
            config=Config(s3={"addressing_style": addressing_style}),
        )
        return self._client

    def normalize_object_key(self, object_key: str) -> str:
        prefix = self.settings.object_storage_prefix.strip().strip("/")
        cleaned = object_key.strip().replace("\\", "/").strip("/")
        parts = [part for part in PurePosixPath(cleaned).parts if part not in {"", "."}]
        if not parts or any(part == ".." or ":" in part for part in parts):
            raise ObjectStorageError("Invalid object storage key.")
        relative_key = "/".join(parts)
        return f"{prefix}/{relative_key}" if prefix else relative_key
