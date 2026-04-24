import { useMemo } from "react";

import type { BreadcrumbItem, ImageDetail } from "../types/api";
import { formatBytes, formatDate } from "../utils/format";
import { imageFileUrl } from "../utils/api";
import { statusLabel } from "../utils/labels";
import { MetadataTable } from "./MetadataTable";

interface ImageDetailDrawerProps {
  image: ImageDetail | null;
  loading: boolean;
  breadcrumbs: BreadcrumbItem[];
  zoom: number;
  fitToScreen: boolean;
  onClose: () => void;
  onZoomChange: (zoom: number) => void;
  onToggleFit: () => void;
}

export function ImageDetailDrawer({
  image,
  loading,
  breadcrumbs,
  zoom,
  fitToScreen,
  onClose,
  onZoomChange,
  onToggleFit,
}: ImageDetailDrawerProps) {
  const breadcrumbText = useMemo(
    () => breadcrumbs.map((item) => item.name).join(" / "),
    [breadcrumbs],
  );

  return (
    <aside className={`detail-drawer ${image ? "open" : ""}`}>
      <div className="detail-header">
        <div>
          <p className="eyebrow">상세 보기</p>
          <h2>{image?.filename ?? "선택된 PNG 없음"}</h2>
          <p className="muted">{breadcrumbText}</p>
        </div>
        <button className="secondary" onClick={onClose}>
          닫기
        </button>
      </div>
      {loading ? <div className="empty-state">상세 정보를 불러오는 중입니다.</div> : null}
      {!loading && image ? (
        <>
          <div className="preview-toolbar">
            <button className="secondary" onClick={() => onZoomChange(Math.max(0.25, zoom - 0.25))}>
              축소
            </button>
            <button className="secondary" onClick={() => onZoomChange(Math.min(4, zoom + 0.25))}>
              확대
            </button>
            <button className="secondary" onClick={onToggleFit}>
              {fitToScreen ? "원본 비율" : "화면 맞춤"}
            </button>
            <a className="button-link" href={imageFileUrl(image.id)} target="_blank" rel="noreferrer">
              원본 열기
            </a>
          </div>
          <div className="preview-frame">
            <img
              src={imageFileUrl(image.id)}
              alt={image.filename}
              style={{
                width: fitToScreen ? "100%" : `${zoom * 100}%`,
                height: "auto",
              }}
            />
          </div>
          <div className="detail-facts">
            <div>
              <span>상태</span>
              <strong>{statusLabel(image.status)}</strong>
            </div>
            <div>
              <span>상대 경로</span>
              <strong>{image.relative_path}</strong>
            </div>
            <div>
              <span>크기</span>
              <strong>
                {image.width ?? "-"} x {image.height ?? "-"}
              </strong>
            </div>
            <div>
              <span>파일 용량</span>
              <strong>{formatBytes(image.file_size_bytes)}</strong>
            </div>
            <div>
              <span>수정 시각</span>
              <strong>{formatDate(image.modified_time)}</strong>
            </div>
            <div>
              <span>포맷 / 모드</span>
              <strong>
                {image.format ?? "-"} / {image.mode ?? "-"}
              </strong>
            </div>
            <div>
              <span>비트 / 컬러 타입</span>
              <strong>
                {image.bit_depth ?? "-"} / {image.color_type ?? "-"}
              </strong>
            </div>
          </div>
          {image.error_message ? <div className="error-box">{image.error_message}</div> : null}
          <MetadataTable metadata={image.metadata} />
        </>
      ) : null}
      {!loading && !image ? <div className="empty-state">목록에서 PNG를 선택해 주세요.</div> : null}
    </aside>
  );
}
