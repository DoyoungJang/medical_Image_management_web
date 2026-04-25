from __future__ import annotations

import mimetypes
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.container import AppContainer
from app.dependencies import get_container, get_db
from app.schemas import (
    HealthResponse,
    ImageDetailResponse,
    ImageListResponse,
    IndexStatusResponse,
    LoginRequest,
    MetadataFacetsResponse,
    MetadataKeysResponse,
    PublicConfigResponse,
    SessionResponse,
    TreeResponse,
)
from app.services.filesystem import PathValidationError
from app.services.search import SearchFilters
from app.services.thumbnails import ThumbnailError

public_router = APIRouter()
protected_router = APIRouter()
admin_router = APIRouter(prefix="/admin")
auth_router = APIRouter(prefix="/auth")


def require_user(request: Request, container: AppContainer = Depends(get_container)):
    return container.auth_service.require_authenticated_user(request)


@public_router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    db.execute(text("SELECT 1"))
    return HealthResponse(status="ok", database="ok")


@public_router.get("/config/public", response_model=PublicConfigResponse)
def public_config(container: AppContainer = Depends(get_container)) -> PublicConfigResponse:
    settings = container.settings
    return PublicConfigResponse(
        app_name=settings.app_name,
        auth_enabled=settings.auth_enabled,
        public_show_absolute_path=settings.public_show_absolute_path,
        supported_image_extensions=settings.supported_image_extensions,
        default_page_size=settings.default_page_size,
        max_page_size=settings.max_page_size,
        thumbnail_default_size=settings.thumbnail_default_size,
        thumbnail_max_size=settings.thumbnail_max_size,
    )


@auth_router.get("/session", response_model=SessionResponse)
def get_session(request: Request, container: AppContainer = Depends(get_container)) -> SessionResponse:
    user = container.auth_service.get_authenticated_user(request)
    if user is None:
        return SessionResponse(authenticated=False)
    return SessionResponse(authenticated=True, username=user.username)


@auth_router.post("/login", response_model=SessionResponse)
def login(
    payload: LoginRequest,
    response: Response,
    container: AppContainer = Depends(get_container),
) -> SessionResponse:
    user = container.auth_service.authenticate_credentials(payload.username, payload.password)
    container.auth_service.set_session_cookie(response, user.username)
    return SessionResponse(authenticated=True, username=user.username)


@auth_router.post("/logout", response_model=SessionResponse)
def logout(response: Response, container: AppContainer = Depends(get_container)) -> SessionResponse:
    container.auth_service.clear_session_cookie(response)
    return SessionResponse(authenticated=False)


@protected_router.get("/tree", response_model=TreeResponse, dependencies=[Depends(require_user)])
def get_tree(
    path: str = Query(default=""),
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
) -> TreeResponse:
    try:
        normalized_path = container.file_system_service.normalize_relative_path(path)
    except PathValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    folders, files, breadcrumbs = container.search_service.get_tree(db, normalized_path)
    return TreeResponse(current_path=normalized_path, breadcrumbs=breadcrumbs, folders=folders, files=files)


@protected_router.get("/images", response_model=ImageListResponse, dependencies=[Depends(require_user)])
def list_images(
    q: str | None = Query(default=None),
    directory: str | None = Query(default=None),
    width_min: int | None = Query(default=None, ge=0),
    width_max: int | None = Query(default=None, ge=0),
    height_min: int | None = Query(default=None, ge=0),
    height_max: int | None = Query(default=None, ge=0),
    size_min: int | None = Query(default=None, ge=0),
    size_max: int | None = Query(default=None, ge=0),
    modified_from: datetime | None = Query(default=None),
    modified_to: datetime | None = Query(default=None),
    has_alpha: bool | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    metadata_key: str | None = Query(default=None),
    metadata_value: str | None = Query(default=None),
    sort: Literal["filename", "path", "file_size", "modified_time", "width", "height"] = Query(default="modified_time"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1),
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
) -> ImageListResponse:
    directory_value = None
    if directory is not None:
        try:
            directory_value = container.file_system_service.normalize_relative_path(directory)
        except PathValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    filters = SearchFilters(
        q=q,
        directory=directory_value,
        width_min=width_min,
        width_max=width_max,
        height_min=height_min,
        height_max=height_max,
        size_min=size_min,
        size_max=size_max,
        modified_from=modified_from,
        modified_to=modified_to,
        has_alpha=has_alpha,
        status=status_filter,
        metadata_key=metadata_key,
        metadata_value=metadata_value,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )
    items, total = container.search_service.search_images(db, filters)
    return ImageListResponse(
        items=[container.search_service.to_image_summary(item) for item in items],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
    )


@protected_router.get("/images/{image_id}", response_model=ImageDetailResponse, dependencies=[Depends(require_user)])
def get_image_detail(
    image_id: int,
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
) -> ImageDetailResponse:
    image = container.search_service.get_image(db, image_id)
    if image is None or image.missing_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="이미지를 찾을 수 없습니다.")

    metadata = container.metadata_extractor.deserialize_metadata(image.metadata_json)
    absolute_path = None
    if container.settings.public_show_absolute_path:
        absolute_path = str(container.file_system_service.resolve_relative_path(image.relative_path, strict=True))

    summary = container.search_service.to_image_summary(image)
    return ImageDetailResponse(
        **summary.model_dump(),
        format=image.format,
        mode=image.mode,
        bit_depth=image.bit_depth,
        color_type=image.color_type,
        dpi_x=image.dpi_x,
        dpi_y=image.dpi_y,
        error_message=image.error_message,
        metadata=metadata,
        absolute_path=absolute_path,
    )


@protected_router.get("/images/{image_id}/thumbnail", dependencies=[Depends(require_user)])
def get_thumbnail(
    image_id: int,
    size: int = Query(default=256, ge=32, le=2048),
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
):
    image = container.search_service.get_image(db, image_id)
    if image is None or image.missing_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="이미지를 찾을 수 없습니다.")
    try:
        thumbnail_path = container.thumbnail_service.get_thumbnail_path(image, size)
    except ThumbnailError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return FileResponse(thumbnail_path, media_type="image/png")


@protected_router.get("/images/{image_id}/file", dependencies=[Depends(require_user)])
def get_original_file(
    image_id: int,
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
):
    image = container.search_service.get_image(db, image_id)
    if image is None or image.missing_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="이미지를 찾을 수 없습니다.")
    try:
        file_path = container.file_system_service.resolve_relative_path(image.relative_path, strict=True)
    except (FileNotFoundError, PathValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="이미지 파일을 사용할 수 없습니다.") from exc
    media_type = mimetypes.guess_type(image.filename)[0] or "application/octet-stream"
    return FileResponse(file_path, media_type=media_type, filename=image.filename)


@protected_router.get("/metadata/keys", response_model=MetadataKeysResponse, dependencies=[Depends(require_user)])
def get_metadata_keys(
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
) -> MetadataKeysResponse:
    return MetadataKeysResponse(keys=container.search_service.get_metadata_keys(db))


@protected_router.get("/metadata/facets", response_model=MetadataFacetsResponse, dependencies=[Depends(require_user)])
def get_metadata_facets(
    q: str | None = Query(default=None),
    directory: str | None = Query(default=None),
    width_min: int | None = Query(default=None, ge=0),
    width_max: int | None = Query(default=None, ge=0),
    height_min: int | None = Query(default=None, ge=0),
    height_max: int | None = Query(default=None, ge=0),
    size_min: int | None = Query(default=None, ge=0),
    size_max: int | None = Query(default=None, ge=0),
    modified_from: datetime | None = Query(default=None),
    modified_to: datetime | None = Query(default=None),
    has_alpha: bool | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    metadata_key: str | None = Query(default=None),
    metadata_value: str | None = Query(default=None),
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
) -> MetadataFacetsResponse:
    directory_value = None
    if directory is not None:
        try:
            directory_value = container.file_system_service.normalize_relative_path(directory)
        except PathValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    filters = SearchFilters(
        q=q,
        directory=directory_value,
        width_min=width_min,
        width_max=width_max,
        height_min=height_min,
        height_max=height_max,
        size_min=size_min,
        size_max=size_max,
        modified_from=modified_from,
        modified_to=modified_to,
        has_alpha=has_alpha,
        status=status_filter,
        metadata_key=metadata_key,
        metadata_value=metadata_value,
    )
    status_counts, directory_counts, common_metadata_keys = container.search_service.get_metadata_facets(db, filters)
    return MetadataFacetsResponse(
        status_counts=status_counts,
        directory_counts=directory_counts,
        common_metadata_keys=common_metadata_keys,
    )


@admin_router.post("/rescan", dependencies=[Depends(require_user)])
def trigger_rescan(container: AppContainer = Depends(get_container)) -> dict[str, str]:
    accepted = container.index_service.trigger_background_scan(reason="manual")
    if not accepted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 스캔 중이거나 너무 빠르게 재요청했습니다.",
        )
    return {"status": "accepted"}


@admin_router.get("/index-status", response_model=IndexStatusResponse, dependencies=[Depends(require_user)])
def index_status(
    db: Session = Depends(get_db),
    container: AppContainer = Depends(get_container),
) -> IndexStatusResponse:
    return IndexStatusResponse(**container.index_service.get_status(db))


api_router = APIRouter()
api_router.include_router(public_router)
api_router.include_router(auth_router)
api_router.include_router(protected_router)
api_router.include_router(admin_router)
