from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Folder(Base):
    __tablename__ = "folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    relative_path: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(512))
    parent_path: Mapped[str] = mapped_column(String(2048), index=True, default="")
    direct_file_count: Mapped[int] = mapped_column(Integer, default=0)
    descendant_file_count: Mapped[int] = mapped_column(Integer, default=0)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    relative_path: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    filename: Mapped[str] = mapped_column(String(512), index=True)
    directory: Mapped[str] = mapped_column(String(2048), index=True, default="")
    extension: Mapped[str] = mapped_column(String(32), default=".png")
    file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    modified_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    format: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    bit_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    has_alpha: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    dpi_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    dpi_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    metadata_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), index=True, default="ok")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    missing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    metadata_entries: Mapped[list["MetadataKV"]] = relationship(
        back_populates="image",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class MetadataKV(Base):
    __tablename__ = "metadata_kv"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(255), index=True)
    value_text: Mapped[str] = mapped_column(Text)
    value_number: Mapped[float | None] = mapped_column(Float, nullable=True)

    image: Mapped[Image] = relationship(back_populates="metadata_entries")


class TrackedMetadataKey(Base):
    __tablename__ = "tracked_metadata_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


Index("ix_images_directory_filename", Image.directory, Image.filename)
Index("ix_metadata_kv_key_value", MetadataKV.key, MetadataKV.value_text)
