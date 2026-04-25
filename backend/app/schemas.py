from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PublicConfigResponse(BaseModel):
    app_name: str
    auth_enabled: bool
    public_show_absolute_path: bool
    supported_image_extensions: list[str]
    default_page_size: int
    max_page_size: int
    thumbnail_default_size: int
    thumbnail_max_size: int


class BreadcrumbItem(BaseModel):
    name: str
    path: str


class FolderNode(BaseModel):
    name: str
    path: str
    direct_file_count: int
    descendant_file_count: int


class MetadataSummaryItem(BaseModel):
    key: str
    value: str


class ImageSummaryResponse(BaseModel):
    id: int
    filename: str
    relative_path: str
    directory: str
    extension: str
    file_size_bytes: int
    modified_time: datetime
    width: int | None
    height: int | None
    status: str
    has_alpha: bool | None
    metadata_summary: list[MetadataSummaryItem] = Field(default_factory=list)


class ImageDetailResponse(ImageSummaryResponse):
    format: str | None
    mode: str | None
    bit_depth: int | None
    color_type: str | None
    dpi_x: float | None
    dpi_y: float | None
    error_message: str | None
    metadata: dict[str, Any]
    absolute_path: str | None = None


class ImageListResponse(BaseModel):
    items: list[ImageSummaryResponse]
    total: int
    page: int
    page_size: int


class TreeResponse(BaseModel):
    current_path: str
    breadcrumbs: list[BreadcrumbItem]
    folders: list[FolderNode]
    files: list[ImageSummaryResponse]


class MetadataKeysResponse(BaseModel):
    keys: list[str]


class FacetCount(BaseModel):
    key: str
    count: int


class MetadataFacetsResponse(BaseModel):
    status_counts: list[FacetCount]
    directory_counts: list[FacetCount]
    common_metadata_keys: list[FacetCount]


class IndexStatusResponse(BaseModel):
    scanning: bool
    last_started_at: datetime | None
    last_finished_at: datetime | None
    last_result: dict[str, Any] | None
    total_images: int
    active_images: int
    missing_images: int


class HealthResponse(BaseModel):
    status: str
    database: str


class LoginRequest(BaseModel):
    username: str
    password: str


class SessionResponse(BaseModel):
    authenticated: bool
    username: str | None = None
    is_admin: bool = False
