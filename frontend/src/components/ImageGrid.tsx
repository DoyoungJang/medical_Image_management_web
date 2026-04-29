import type { ImageSummary } from "../types/api";
import type { ImageViewMode } from "../types/api";
import { formatBytes, formatDate } from "../utils/format";
import { imageThumbnailUrl } from "../utils/api";
import { statusLabel } from "../utils/labels";

interface ImageGridProps {
  items: ImageSummary[];
  loading: boolean;
  selectedImageId: number | null;
  selectedImageIds: Set<number>;
  thumbnailSize: number;
  viewMode: ImageViewMode;
  onSelect: (imageId: number) => void;
  onToggleSelected: (imageId: number) => void;
}

export function ImageGrid({
  items,
  loading,
  selectedImageId,
  selectedImageIds,
  thumbnailSize,
  viewMode,
  onSelect,
  onToggleSelected,
}: ImageGridProps) {
  if (loading) {
    return <div className="panel empty-state">이미지 목록을 불러오는 중입니다.</div>;
  }

  if (!items.length) {
    return <div className="panel empty-state">조건에 맞는 이미지 파일이 없습니다.</div>;
  }

  if (viewMode === "details") {
    return (
      <div className="file-list" role="table" aria-label="이미지 파일 목록">
        <div className="file-list-row file-list-head" role="row">
          <span />
          <span>파일명</span>
          <span>폴더</span>
          <span>크기</span>
          <span>수정 시각</span>
          <span>상태</span>
        </div>
        {items.map((item) => (
          <div
            key={item.id}
            className={`file-list-row ${selectedImageId === item.id ? "focused" : ""} ${
              selectedImageIds.has(item.id) ? "checked" : ""
            }`}
            role="row"
            onClick={() => onSelect(item.id)}
          >
            <input
              type="checkbox"
              checked={selectedImageIds.has(item.id)}
              aria-label={`${item.filename} 선택`}
              onClick={(event) => event.stopPropagation()}
              onChange={() => onToggleSelected(item.id)}
            />
            <button className="file-name-button" type="button" onClick={() => onSelect(item.id)}>
              {item.filename}
            </button>
            <span>{item.directory || "루트"}</span>
            <span>{formatBytes(item.file_size_bytes)}</span>
            <span>{formatDate(item.modified_time)}</span>
            <span>{statusLabel(item.status)}</span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={`image-grid ${viewMode === "imageOnly" ? "image-only" : ""}`}>
      {items.map((item) => (
        <div
          key={item.id}
          className={`image-card ${selectedImageId === item.id ? "selected" : ""}`}
          role="button"
          tabIndex={0}
          onClick={() => onSelect(item.id)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              onSelect(item.id);
            }
          }}
        >
          <span className="selection-check" onClick={(event) => event.stopPropagation()}>
            <input
              type="checkbox"
              checked={selectedImageIds.has(item.id)}
              aria-label={`${item.filename} 선택`}
              onChange={() => onToggleSelected(item.id)}
            />
          </span>
          <div className="image-card-thumb">
            <img src={imageThumbnailUrl(item.id, thumbnailSize)} alt={item.filename} loading="lazy" />
          </div>
          {viewMode === "grid" ? (
            <div className="image-card-body">
              <div className="image-card-header">
                <strong>{item.filename}</strong>
                <div className="image-card-badges">
                  <span className="format-pill">{item.extension.replace(".", "").toUpperCase()}</span>
                  <span className={`status-pill ${item.status}`}>{statusLabel(item.status)}</span>
                </div>
              </div>
              <p>{item.relative_path}</p>
              <p>
                {item.width ?? "-"} x {item.height ?? "-"} / {formatBytes(item.file_size_bytes)}
              </p>
              <p>{formatDate(item.modified_time)}</p>
              <div className="metadata-summary">
                {Object.entries(item.tracked_metadata).map(([key, value]) => (
                  <span key={`${item.id}-tracked-${key}`} className={`chip tracked-chip ${value === null ? "null" : ""}`}>
                    {key}: {value ?? "null"}
                  </span>
                ))}
                {item.metadata_summary.map((summary) => (
                  <span key={`${item.id}-${summary.key}`} className="chip">
                    {summary.key}: {summary.value}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
