import type { ImageSummary } from "../types/api";
import { formatBytes, formatDate } from "../utils/format";
import { imageThumbnailUrl } from "../utils/api";
import { statusLabel } from "../utils/labels";

interface ImageGridProps {
  items: ImageSummary[];
  loading: boolean;
  selectedImageId: number | null;
  thumbnailSize: number;
  onSelect: (imageId: number) => void;
}

export function ImageGrid({ items, loading, selectedImageId, thumbnailSize, onSelect }: ImageGridProps) {
  if (loading) {
    return <div className="panel empty-state">이미지 목록을 불러오는 중입니다.</div>;
  }

  if (!items.length) {
    return <div className="panel empty-state">조건에 맞는 PNG 파일이 없습니다.</div>;
  }

  return (
    <div className="image-grid">
      {items.map((item) => (
        <button
          key={item.id}
          className={`image-card ${selectedImageId === item.id ? "selected" : ""}`}
          onClick={() => onSelect(item.id)}
        >
          <div className="image-card-thumb">
            <img src={imageThumbnailUrl(item.id, thumbnailSize)} alt={item.filename} loading="lazy" />
          </div>
          <div className="image-card-body">
            <div className="image-card-header">
              <strong>{item.filename}</strong>
              <span className={`status-pill ${item.status}`}>{statusLabel(item.status)}</span>
            </div>
            <p>{item.relative_path}</p>
            <p>
              {item.width ?? "-"} x {item.height ?? "-"} / {formatBytes(item.file_size_bytes)}
            </p>
            <p>{formatDate(item.modified_time)}</p>
            <div className="metadata-summary">
              {item.metadata_summary.map((summary) => (
                <span key={`${item.id}-${summary.key}`} className="chip">
                  {summary.key}: {summary.value}
                </span>
              ))}
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}
