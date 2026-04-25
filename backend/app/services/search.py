from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, delete, exists, func, or_, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.core.config import Settings
from app.models import Folder, Image, MetadataKV
from app.schemas import BreadcrumbItem, FacetCount, FolderNode, ImageSummaryResponse, MetadataSummaryItem


@dataclass(slots=True)
class SearchFilters:
    q: str | None = None
    directory: str | None = None
    width_min: int | None = None
    width_max: int | None = None
    height_min: int | None = None
    height_max: int | None = None
    size_min: int | None = None
    size_max: int | None = None
    modified_from: datetime | None = None
    modified_to: datetime | None = None
    has_alpha: bool | None = None
    status: str | None = None
    metadata_key: str | None = None
    metadata_value: str | None = None
    sort: str = "modified_time"
    order: str = "desc"
    page: int = 1
    page_size: int = 24


class SearchService:
    def __init__(self, settings: Settings, session_factory: sessionmaker[Session]) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self._fts_enabled = False

    @property
    def fts_enabled(self) -> bool:
        return self._fts_enabled

    def initialize(self) -> None:
        if not self.settings.use_fts5 or not self.settings.database_url.startswith("sqlite"):
            self._fts_enabled = False
            return
        try:
            with self.session_factory() as session:
                session.execute(
                    text(
                        """
                        CREATE VIRTUAL TABLE IF NOT EXISTS images_fts
                        USING fts5(relative_path, filename, directory, metadata_text)
                        """
                    )
                )
                session.commit()
            self._fts_enabled = True
        except SQLAlchemyError:
            self._fts_enabled = False

    def rebuild_search_indexes(self, session: Session, *, indexed_at: datetime) -> None:
        self._rebuild_folder_table(session, indexed_at=indexed_at)
        if self._fts_enabled:
            session.execute(text("DELETE FROM images_fts"))
            session.execute(
                text(
                    """
                    INSERT INTO images_fts(rowid, relative_path, filename, directory, metadata_text)
                    SELECT id, relative_path, filename, directory, metadata_text
                    FROM images
                    WHERE missing_at IS NULL
                    """
                )
            )

    def _rebuild_folder_table(self, session: Session, *, indexed_at: datetime) -> None:
        active_images = session.execute(
            select(Image.relative_path, Image.directory).where(Image.missing_at.is_(None))
        ).all()

        stats: dict[str, dict[str, Any]] = {
            "": {
                "name": "",
                "parent_path": "",
                "direct_file_count": 0,
                "descendant_file_count": 0,
            }
        }

        for relative_path, directory in active_images:
            stats[""]["descendant_file_count"] += 1
            if not directory:
                stats[""]["direct_file_count"] += 1
                continue

            parts = [part for part in directory.split("/") if part]
            current_path = ""
            for index, part in enumerate(parts):
                parent_path = current_path
                current_path = part if not current_path else f"{current_path}/{part}"
                item = stats.setdefault(
                    current_path,
                    {
                        "name": part,
                        "parent_path": parent_path,
                        "direct_file_count": 0,
                        "descendant_file_count": 0,
                    },
                )
                item["descendant_file_count"] += 1
                if index == len(parts) - 1:
                    item["direct_file_count"] += 1

        session.execute(delete(Folder))
        folders = [
            Folder(
                relative_path=relative_path,
                name=values["name"],
                parent_path=values["parent_path"],
                direct_file_count=values["direct_file_count"],
                descendant_file_count=values["descendant_file_count"],
                indexed_at=indexed_at,
            )
            for relative_path, values in stats.items()
        ]
        session.add_all(folders)

    def get_image(self, session: Session, image_id: int) -> Image | None:
        statement = (
            select(Image)
            .where(Image.id == image_id)
            .options(selectinload(Image.metadata_entries))
        )
        return session.execute(statement).scalar_one_or_none()

    def search_images(self, session: Session, filters: SearchFilters) -> tuple[list[Image], int]:
        filters.page = max(filters.page, 1)
        filters.page_size = min(max(filters.page_size, 1), self.settings.max_page_size)

        query = (
            select(Image)
            .where(Image.missing_at.is_(None))
            .options(selectinload(Image.metadata_entries))
        )
        count_query = select(func.count(Image.id)).where(Image.missing_at.is_(None))
        query, count_query = self._apply_filters(query, count_query, filters)

        order_column = self._sort_column(filters.sort)
        if filters.order.lower() == "asc":
            query = query.order_by(order_column.asc(), Image.id.asc())
        else:
            query = query.order_by(order_column.desc(), Image.id.desc())

        total = session.execute(count_query).scalar_one()
        offset = (filters.page - 1) * filters.page_size
        items = session.execute(query.offset(offset).limit(filters.page_size)).scalars().all()
        return items, total

    def _apply_filters(self, query: Any, count_query: Any, filters: SearchFilters) -> tuple[Any, Any]:
        conditions = []
        params: dict[str, Any] = {}

        if filters.directory:
            directory = filters.directory.strip("/")
            conditions.append(or_(Image.directory == directory, Image.directory.like(f"{directory}/%")))

        if filters.width_min is not None:
            conditions.append(Image.width >= filters.width_min)
        if filters.width_max is not None:
            conditions.append(Image.width <= filters.width_max)
        if filters.height_min is not None:
            conditions.append(Image.height >= filters.height_min)
        if filters.height_max is not None:
            conditions.append(Image.height <= filters.height_max)
        if filters.size_min is not None:
            conditions.append(Image.file_size_bytes >= filters.size_min)
        if filters.size_max is not None:
            conditions.append(Image.file_size_bytes <= filters.size_max)
        if filters.modified_from is not None:
            conditions.append(Image.modified_time >= filters.modified_from)
        if filters.modified_to is not None:
            conditions.append(Image.modified_time <= filters.modified_to)
        if filters.has_alpha is not None:
            conditions.append(Image.has_alpha.is_(filters.has_alpha))
        if filters.status:
            conditions.append(Image.status == filters.status)

        if filters.metadata_key and filters.metadata_value:
            conditions.append(
                exists(
                    select(MetadataKV.id).where(
                        MetadataKV.image_id == Image.id,
                        MetadataKV.key == filters.metadata_key,
                        MetadataKV.value_text.ilike(f"%{filters.metadata_value}%"),
                    )
                )
            )
        elif filters.metadata_key:
            conditions.append(
                exists(select(MetadataKV.id).where(MetadataKV.image_id == Image.id, MetadataKV.key == filters.metadata_key))
            )

        if filters.q:
            fts_query = self._build_fts_query(filters.q)
            if self._fts_enabled and fts_query:
                fts_condition = text("images.id IN (SELECT rowid FROM images_fts WHERE images_fts MATCH :fts_query)")
                conditions.append(fts_condition)
                params["fts_query"] = fts_query
            else:
                like_value = f"%{filters.q}%"
                conditions.append(
                    or_(
                        Image.filename.ilike(like_value),
                        Image.relative_path.ilike(like_value),
                        Image.metadata_text.ilike(like_value),
                        exists(
                            select(MetadataKV.id).where(
                                MetadataKV.image_id == Image.id,
                                or_(
                                    MetadataKV.key.ilike(like_value),
                                    MetadataKV.value_text.ilike(like_value),
                                ),
                            )
                        ),
                    )
                )

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        if params:
            query = query.params(**params)
            count_query = count_query.params(**params)
        return query, count_query

    def _build_fts_query(self, raw_query: str) -> str:
        tokens = re.findall(r"[0-9A-Za-z_\u3131-\u318E\uAC00-\uD7A3]+", raw_query)
        if not tokens:
            return ""
        return " AND ".join(f"{token}*" for token in tokens[:8])

    def _sort_column(self, sort_key: str) -> Any:
        mapping = {
            "filename": Image.filename,
            "path": Image.relative_path,
            "file_size": Image.file_size_bytes,
            "modified_time": Image.modified_time,
            "width": Image.width,
            "height": Image.height,
        }
        return mapping.get(sort_key, Image.modified_time)

    def get_tree(self, session: Session, current_path: str) -> tuple[list[FolderNode], list[ImageSummaryResponse], list[BreadcrumbItem]]:
        folder_query = (
            select(Folder)
            .where(Folder.parent_path == current_path, Folder.relative_path != current_path)
            .order_by(Folder.name.asc())
        )
        folders = [
            FolderNode(
                name=folder.name,
                path=folder.relative_path,
                direct_file_count=folder.direct_file_count,
                descendant_file_count=folder.descendant_file_count,
            )
            for folder in session.execute(folder_query).scalars().all()
        ]

        file_query = (
            select(Image)
            .where(Image.directory == current_path, Image.missing_at.is_(None))
            .options(selectinload(Image.metadata_entries))
            .order_by(Image.filename.asc())
        )
        files = [self.to_image_summary(image) for image in session.execute(file_query).scalars().all()]
        return folders, files, self._breadcrumbs(current_path)

    def _breadcrumbs(self, current_path: str) -> list[BreadcrumbItem]:
        breadcrumbs = [BreadcrumbItem(name="루트", path="")]
        if not current_path:
            return breadcrumbs
        parts = [part for part in current_path.split("/") if part]
        cumulative = ""
        for part in parts:
            cumulative = part if not cumulative else f"{cumulative}/{part}"
            breadcrumbs.append(BreadcrumbItem(name=part, path=cumulative))
        return breadcrumbs

    def to_image_summary(self, image: Image) -> ImageSummaryResponse:
        metadata_summary = [
            MetadataSummaryItem(key=entry.key, value=entry.value_text)
            for entry in sorted(image.metadata_entries, key=lambda item: item.key)[:3]
        ]
        return ImageSummaryResponse(
            id=image.id,
            filename=image.filename,
            relative_path=image.relative_path,
            directory=image.directory,
            extension=image.extension,
            file_size_bytes=image.file_size_bytes,
            modified_time=image.modified_time,
            width=image.width,
            height=image.height,
            status=image.status,
            has_alpha=image.has_alpha,
            metadata_summary=metadata_summary,
        )

    def get_metadata_keys(self, session: Session, limit: int = 100) -> list[str]:
        query = (
            select(MetadataKV.key, func.count(MetadataKV.id).label("count"))
            .join(Image, Image.id == MetadataKV.image_id)
            .where(Image.missing_at.is_(None))
            .group_by(MetadataKV.key)
            .order_by(func.count(MetadataKV.id).desc(), MetadataKV.key.asc())
            .limit(limit)
        )
        return [row[0] for row in session.execute(query).all()]

    def get_metadata_facets(self, session: Session, filters: SearchFilters) -> tuple[list[FacetCount], list[FacetCount], list[FacetCount]]:
        filtered_ids = self._filtered_image_ids_subquery(filters)

        status_query = (
            select(Image.status, func.count(Image.id))
            .where(Image.id.in_(filtered_ids))
            .group_by(Image.status)
            .order_by(func.count(Image.id).desc(), Image.status.asc())
        )
        directory_query = (
            select(Image.directory, func.count(Image.id))
            .where(Image.id.in_(filtered_ids))
            .group_by(Image.directory)
            .order_by(func.count(Image.id).desc(), Image.directory.asc())
            .limit(25)
        )
        metadata_query = (
            select(MetadataKV.key, func.count(MetadataKV.id))
            .join(Image, Image.id == MetadataKV.image_id)
            .where(Image.id.in_(filtered_ids))
            .group_by(MetadataKV.key)
            .order_by(func.count(MetadataKV.id).desc(), MetadataKV.key.asc())
            .limit(25)
        )

        status_counts = [FacetCount(key=row[0], count=row[1]) for row in session.execute(status_query).all()]
        directory_counts = [FacetCount(key=row[0], count=row[1]) for row in session.execute(directory_query).all()]
        metadata_counts = [FacetCount(key=row[0], count=row[1]) for row in session.execute(metadata_query).all()]
        return status_counts, directory_counts, metadata_counts

    def _filtered_image_ids_subquery(self, filters: SearchFilters) -> Any:
        query = select(Image.id).where(Image.missing_at.is_(None))
        count_query = select(func.count(Image.id)).where(Image.missing_at.is_(None))
        query, _ = self._apply_filters(query, count_query, filters)
        return query

    def get_index_counts(self, session: Session) -> dict[str, int]:
        total_images = session.execute(select(func.count(Image.id))).scalar_one()
        active_images = session.execute(select(func.count(Image.id)).where(Image.missing_at.is_(None))).scalar_one()
        missing_images = session.execute(select(func.count(Image.id)).where(Image.missing_at.is_not(None))).scalar_one()
        return {
            "total_images": total_images,
            "active_images": active_images,
            "missing_images": missing_images,
        }
