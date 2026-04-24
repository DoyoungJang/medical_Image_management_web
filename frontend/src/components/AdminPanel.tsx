import type { FacetCount, IndexStatusResponse } from "../types/api";

interface AdminPanelProps {
  indexStatus: IndexStatusResponse | null;
  facets: {
    status_counts: FacetCount[];
    directory_counts: FacetCount[];
    common_metadata_keys: FacetCount[];
  } | null;
  loading: boolean;
  rescanning: boolean;
  onRescan: () => Promise<void>;
}

export function AdminPanel({ indexStatus, facets, loading, rescanning, onRescan }: AdminPanelProps) {
  return (
    <div className="panel admin-panel">
      <div className="panel-header">
        <h2>인덱스 상태</h2>
        <button onClick={onRescan} disabled={rescanning}>
          {rescanning ? "재스캔 요청 중..." : "재스캔"}
        </button>
      </div>
      {loading || !indexStatus ? (
        <p className="muted">인덱스 상태를 불러오는 중입니다...</p>
      ) : (
        <>
          <div className="stat-row">
            <span>스캔 중</span>
            <strong>{indexStatus.scanning ? "예" : "아니오"}</strong>
          </div>
          <div className="stat-row">
            <span>활성 이미지</span>
            <strong>{indexStatus.active_images}</strong>
          </div>
          <div className="stat-row">
            <span>누락 표시</span>
            <strong>{indexStatus.missing_images}</strong>
          </div>
          <div className="stat-row">
            <span>전체 레코드</span>
            <strong>{indexStatus.total_images}</strong>
          </div>
          <div className="facet-section">
            <h3>상태 집계</h3>
            <div className="chip-wrap">
              {(facets?.status_counts ?? []).map((item) => (
                <span key={item.key} className="chip">
                  {item.key}: {item.count}
                </span>
              ))}
            </div>
          </div>
          <div className="facet-section">
            <h3>자주 쓰는 메타데이터 키</h3>
            <div className="chip-wrap">
              {(facets?.common_metadata_keys ?? []).map((item) => (
                <span key={item.key} className="chip">
                  {item.key}: {item.count}
                </span>
              ))}
            </div>
          </div>
          <div className="facet-section">
            <h3>주요 디렉터리</h3>
            <div className="chip-wrap">
              {(facets?.directory_counts ?? []).map((item) => (
                <span key={item.key} className="chip">
                  {item.key || "루트"}: {item.count}
                </span>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
