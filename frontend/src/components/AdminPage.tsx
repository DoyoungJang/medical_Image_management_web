import type { FacetCount, IndexStatusResponse, PublicConfig } from "../types/api";
import { booleanLabel, statusLabel } from "../utils/labels";
import { formatDate } from "../utils/format";

interface AdminPageProps {
  config: PublicConfig;
  indexStatus: IndexStatusResponse | null;
  facets: {
    status_counts: FacetCount[];
    directory_counts: FacetCount[];
    common_metadata_keys: FacetCount[];
  } | null;
  loading: boolean;
  rescanning: boolean;
  canRescan: boolean;
  onRescan: () => Promise<void>;
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function FacetList({ title, items, mapKey }: { title: string; items: FacetCount[]; mapKey?: (key: string) => string }) {
  return (
    <section className="admin-section">
      <div className="section-header">
        <h3>{title}</h3>
      </div>
      {items.length ? (
        <div className="facet-list">
          {items.map((item) => (
            <div key={item.key || "root"} className="facet-row">
              <span>{mapKey ? mapKey(item.key) : item.key || "루트"}</span>
              <strong>{item.count}</strong>
            </div>
          ))}
        </div>
      ) : (
        <p className="empty-inline">집계 데이터가 없습니다.</p>
      )}
    </section>
  );
}

export function AdminPage({ config, indexStatus, facets, loading, rescanning, canRescan, onRescan }: AdminPageProps) {
  const lastStartedAt = indexStatus?.last_started_at ? formatDate(indexStatus.last_started_at) : "-";
  const lastFinishedAt = indexStatus?.last_finished_at ? formatDate(indexStatus.last_finished_at) : "-";

  return (
    <main className="admin-page">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">관리자</p>
          <h2>인덱스 및 운영 상태</h2>
        </div>
        <button onClick={onRescan} disabled={!canRescan || rescanning || indexStatus?.scanning}>
          {rescanning ? "재스캔 요청 중" : "수동 재스캔"}
        </button>
      </div>

      {loading && !indexStatus ? <div className="panel empty-state">관리자 정보를 불러오는 중입니다...</div> : null}

      <section className="stat-grid">
        <StatCard label="스캔 진행" value={indexStatus?.scanning ? "진행 중" : "대기"} />
        <StatCard label="활성 이미지" value={indexStatus?.active_images ?? 0} />
        <StatCard label="누락 레코드" value={indexStatus?.missing_images ?? 0} />
        <StatCard label="전체 레코드" value={indexStatus?.total_images ?? 0} />
      </section>

      <section className="admin-section">
        <div className="section-header">
          <h3>최근 스캔</h3>
        </div>
        <div className="info-grid">
          <div>
            <span>마지막 시작</span>
            <strong>{lastStartedAt}</strong>
          </div>
          <div>
            <span>마지막 종료</span>
            <strong>{lastFinishedAt}</strong>
          </div>
          <div>
            <span>마지막 결과</span>
            <strong>{indexStatus?.last_result ? JSON.stringify(indexStatus.last_result) : "-"}</strong>
          </div>
        </div>
      </section>

      <section className="admin-section">
        <div className="section-header">
          <h3>보안 및 공개 설정</h3>
        </div>
        <div className="info-grid">
          <div>
            <span>인증 사용</span>
            <strong>{booleanLabel(config.auth_enabled)}</strong>
          </div>
          <div>
            <span>절대 경로 표시</span>
            <strong>{booleanLabel(config.public_show_absolute_path)}</strong>
          </div>
          <div>
            <span>기본 페이지 크기</span>
            <strong>{config.default_page_size}</strong>
          </div>
          <div>
            <span>최대 페이지 크기</span>
            <strong>{config.max_page_size}</strong>
          </div>
        </div>
      </section>

      <div className="admin-grid">
        <FacetList title="상태별 이미지" items={facets?.status_counts ?? []} mapKey={statusLabel} />
        <FacetList title="주요 디렉터리" items={facets?.directory_counts ?? []} />
        <FacetList title="자주 발견된 메타데이터 키" items={facets?.common_metadata_keys ?? []} />
      </div>
    </main>
  );
}
