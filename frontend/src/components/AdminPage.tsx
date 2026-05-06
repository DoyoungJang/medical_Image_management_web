import { useEffect, useState } from "react";

import type {
  AdminExportRootResponse,
  AdminImageRootResponse,
  AdminSignupCodeResponse,
  FacetCount,
  IndexStatusResponse,
  PublicConfig,
} from "../types/api";
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
  metadataKeys: string[];
  trackedMetadataKeys: string[];
  imageRootConfig: AdminImageRootResponse | null;
  exportRootConfig: AdminExportRootResponse | null;
  signupCodeConfig: AdminSignupCodeResponse | null;
  rootUpdating: boolean;
  exportRootUpdating: boolean;
  signupCodeUpdating: boolean;
  onRescan: () => Promise<void>;
  onUpdateImageRoot: (rootDir: string) => Promise<AdminImageRootResponse>;
  onUpdateExportRoot: (rootDir: string) => Promise<AdminExportRootResponse>;
  onUpdateSignupCode: (signupCode: string) => Promise<AdminSignupCodeResponse>;
  onAddTrackedMetadataKey: (key: string) => Promise<void>;
  onRemoveTrackedMetadataKey: (key: string) => Promise<void>;
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

export function AdminPage({
  config,
  indexStatus,
  facets,
  loading,
  rescanning,
  canRescan,
  metadataKeys,
  trackedMetadataKeys,
  imageRootConfig,
  exportRootConfig,
  signupCodeConfig,
  rootUpdating,
  exportRootUpdating,
  signupCodeUpdating,
  onRescan,
  onUpdateImageRoot,
  onUpdateExportRoot,
  onUpdateSignupCode,
  onAddTrackedMetadataKey,
  onRemoveTrackedMetadataKey,
}: AdminPageProps) {
  const [trackedKeyInput, setTrackedKeyInput] = useState("");
  const [metadataKeySaving, setMetadataKeySaving] = useState(false);
  const [metadataKeyError, setMetadataKeyError] = useState("");
  const [rootInput, setRootInput] = useState("");
  const [rootMessage, setRootMessage] = useState("");
  const [rootError, setRootError] = useState("");
  const [exportRootInput, setExportRootInput] = useState("");
  const [exportRootMessage, setExportRootMessage] = useState("");
  const [exportRootError, setExportRootError] = useState("");
  const [signupCodeInput, setSignupCodeInput] = useState("");
  const [signupCodeMessage, setSignupCodeMessage] = useState("");
  const [signupCodeError, setSignupCodeError] = useState("");
  const lastStartedAt = indexStatus?.last_started_at ? formatDate(indexStatus.last_started_at) : "-";
  const lastFinishedAt = indexStatus?.last_finished_at ? formatDate(indexStatus.last_finished_at) : "-";
  const rootSourceLabel = imageRootConfig?.source === "database" ? "관리자 설정" : "환경 변수";
  const exportRootSourceLabel = exportRootConfig?.source === "database" ? "관리자 설정" : "환경 변수";
  const signupCodeSourceLabel = signupCodeConfig?.source === "database" ? "관리자 설정" : "환경 변수";
  const rescanButtonLabel = !canRescan
    ? "관리자 권한 필요"
    : rescanning
      ? "재스캔 요청 중"
      : indexStatus?.scanning
        ? "스캔 진행 중"
        : "수동 재스캔";

  useEffect(() => {
    if (imageRootConfig?.root_dir) {
      setRootInput(imageRootConfig.root_dir);
    }
  }, [imageRootConfig?.root_dir]);

  useEffect(() => {
    if (exportRootConfig?.root_dir) {
      setExportRootInput(exportRootConfig.root_dir);
    }
  }, [exportRootConfig?.root_dir]);

  useEffect(() => {
    if (signupCodeConfig?.signup_code !== undefined) {
      setSignupCodeInput(signupCodeConfig.signup_code);
    }
  }, [signupCodeConfig?.signup_code]);

  return (
    <main className="admin-page">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">관리자</p>
          <h2>인덱스 및 운영 상태</h2>
        </div>
        <button onClick={onRescan} disabled={!canRescan || rescanning || indexStatus?.scanning}>
          {rescanButtonLabel}
        </button>
      </div>

      {loading && !indexStatus ? <div className="panel empty-state">관리자 정보를 불러오는 중입니다...</div> : null}

      <section className="stat-grid">
        <StatCard label="스캔 진행" value={indexStatus?.scanning ? "진행 중" : "대기"} />
        <StatCard label="활성 이미지" value={indexStatus?.active_images ?? 0} />
        <StatCard label="기존 누락 레코드" value={indexStatus?.missing_images ?? 0} />
        <StatCard label="전체 레코드" value={indexStatus?.total_images ?? 0} />
      </section>

      <section className="admin-section">
        <div className="section-header">
          <div>
            <h3>서버 저장 경로</h3>
            <p className="muted">필터 결과를 서버에 저장할 때 사용하는 기본 경로입니다. 환경변수를 바꾸지 않아도 이 설정이 우선 적용됩니다.</p>
          </div>
        </div>
        <div className="info-grid">
          <div>
            <span>현재 저장 경로</span>
            <strong>{exportRootConfig?.root_dir ?? "관리자 권한으로만 확인 가능"}</strong>
          </div>
          <div>
            <span>설정 출처</span>
            <strong>{exportRootConfig ? exportRootSourceLabel : "-"}</strong>
          </div>
          <div>
            <span>환경 변수 기본값</span>
            <strong>{exportRootConfig?.env_root_dir ?? "-"}</strong>
          </div>
        </div>
        <form
          className="root-path-form"
          onSubmit={async (event) => {
            event.preventDefault();
            const nextRoot = exportRootInput.trim();
            if (!nextRoot) {
              return;
            }
            setExportRootMessage("");
            setExportRootError("");
            try {
              await onUpdateExportRoot(nextRoot);
              setExportRootMessage("서버 저장 경로를 변경했습니다.");
            } catch (error) {
              setExportRootError(error instanceof Error ? error.message : "서버 저장 경로를 변경하지 못했습니다.");
            }
          }}
        >
          <label>
            새 서버 저장 경로
            <input
              value={exportRootInput}
              placeholder="예: C:\\data\\exports 또는 /data/exports"
              disabled={!canRescan || exportRootUpdating}
              onChange={(event) => setExportRootInput(event.target.value)}
            />
          </label>
          <button type="submit" disabled={!canRescan || exportRootUpdating || !exportRootInput.trim()}>
            {exportRootUpdating ? "변경 중" : "저장 경로 변경"}
          </button>
        </form>
        {exportRootMessage ? <p className="success-inline">{exportRootMessage}</p> : null}
        {exportRootError ? <div className="error-box">{exportRootError}</div> : null}
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

      <section className="admin-section">
        <div className="section-header">
          <div>
            <h3>가입 코드</h3>
            <p className="muted">회원가입 화면에서 이 코드를 입력한 사용자만 새 계정을 만들 수 있습니다.</p>
          </div>
        </div>
        <div className="info-grid">
          <div>
            <span>현재 가입 코드</span>
            <strong>{signupCodeConfig?.signup_code || "설정되지 않음"}</strong>
          </div>
          <div>
            <span>설정 출처</span>
            <strong>{signupCodeConfig ? signupCodeSourceLabel : "-"}</strong>
          </div>
          <div>
            <span>가입 조건</span>
            <strong>{signupCodeConfig?.signup_code ? "코드 필요" : "가입 불가"}</strong>
          </div>
        </div>
        <form
          className="root-path-form"
          onSubmit={async (event) => {
            event.preventDefault();
            const nextCode = signupCodeInput.trim();
            if (!nextCode) {
              return;
            }
            setSignupCodeMessage("");
            setSignupCodeError("");
            try {
              await onUpdateSignupCode(nextCode);
              setSignupCodeMessage("가입 코드를 변경했습니다.");
            } catch (error) {
              setSignupCodeError(error instanceof Error ? error.message : "가입 코드를 변경하지 못했습니다.");
            }
          }}
        >
          <label>
            새 가입 코드
            <input
              value={signupCodeInput}
              disabled={!canRescan || signupCodeUpdating}
              onChange={(event) => setSignupCodeInput(event.target.value)}
            />
          </label>
          <button type="submit" disabled={!canRescan || signupCodeUpdating || signupCodeInput.trim().length < 4}>
            {signupCodeUpdating ? "변경 중" : "가입 코드 변경"}
          </button>
        </form>
        {signupCodeMessage ? <p className="success-inline">{signupCodeMessage}</p> : null}
        {signupCodeError ? <div className="error-box">{signupCodeError}</div> : null}
      </section>

      <section className="admin-section">
        <div className="section-header">
          <div>
            <h3>이미지 루트 경로</h3>
            <p className="muted">관리자만 변경할 수 있습니다. 변경하면 기존 목록을 안전하게 비우고 새 경로를 백그라운드로 재스캔합니다.</p>
          </div>
        </div>
        <div className="info-grid">
          <div>
            <span>현재 경로</span>
            <strong>{imageRootConfig?.root_dir ?? "관리자 권한으로만 확인 가능"}</strong>
          </div>
          <div>
            <span>설정 출처</span>
            <strong>{imageRootConfig ? rootSourceLabel : "-"}</strong>
          </div>
          <div>
            <span>환경 변수 기본값</span>
            <strong>{imageRootConfig?.env_root_dir ?? "-"}</strong>
          </div>
        </div>
        <form
          className="root-path-form"
          onSubmit={async (event) => {
            event.preventDefault();
            const nextRoot = rootInput.trim();
            if (!nextRoot) {
              return;
            }
            setRootMessage("");
            setRootError("");
            try {
              const result = await onUpdateImageRoot(nextRoot);
              setRootMessage(
                result.rescan_accepted
                  ? "이미지 루트 경로를 변경했고 재스캔을 요청했습니다."
                  : "이미지 루트 경로를 저장했습니다. 재스캔이 이미 진행 중이면 완료 후 다시 확인하세요.",
              );
            } catch (error) {
              setRootError(error instanceof Error ? error.message : "이미지 루트 경로를 변경하지 못했습니다.");
            }
          }}
        >
          <label>
            새 이미지 루트 경로
            <input
              value={rootInput}
              placeholder="예: C:\\data\\company-png 또는 /data/company-png"
              disabled={!canRescan || rootUpdating || indexStatus?.scanning}
              onChange={(event) => setRootInput(event.target.value)}
            />
          </label>
          <button
            type="submit"
            disabled={!canRescan || rootUpdating || Boolean(indexStatus?.scanning) || !rootInput.trim()}
          >
            {rootUpdating ? "변경 중" : "경로 변경"}
          </button>
        </form>
        {rootMessage ? <p className="success-inline">{rootMessage}</p> : null}
        {rootError ? <div className="error-box">{rootError}</div> : null}
        <p className="empty-inline">
          새 경로는 서버에서 실제로 존재하는 디렉터리여야 하며, 썸네일 캐시 디렉터리가 이미지 루트 안에 있으면 사용할 수 없습니다.
        </p>
      </section>

      <section className="admin-section">
        <div className="section-header">
          <div>
            <h3>관리자 지정 메타데이터</h3>
            <p className="muted">예: View를 등록하면 이미지마다 View 값이 표시되고, 없으면 null로 표시됩니다.</p>
          </div>
        </div>
        <form
          className="tracked-metadata-form"
          onSubmit={async (event) => {
            event.preventDefault();
            const key = trackedKeyInput.trim();
            if (!key) {
              return;
            }
            setMetadataKeySaving(true);
            setMetadataKeyError("");
            try {
              await onAddTrackedMetadataKey(key);
              setTrackedKeyInput("");
            } catch (error) {
              setMetadataKeyError(error instanceof Error ? error.message : "메타데이터 키를 추가하지 못했습니다.");
            } finally {
              setMetadataKeySaving(false);
            }
          }}
        >
          <label>
            표시할 메타데이터 키
            <input
              value={trackedKeyInput}
              list="admin-metadata-keys"
              placeholder="예: View"
              disabled={!canRescan || metadataKeySaving}
              onChange={(event) => setTrackedKeyInput(event.target.value)}
            />
          </label>
          <datalist id="admin-metadata-keys">
            {metadataKeys.map((key) => (
              <option key={key} value={key} />
            ))}
          </datalist>
          <button type="submit" disabled={!canRescan || metadataKeySaving || !trackedKeyInput.trim()}>
            {metadataKeySaving ? "추가 중" : "키 추가"}
          </button>
        </form>
        {metadataKeyError ? <div className="error-box">{metadataKeyError}</div> : null}
        {trackedMetadataKeys.length ? (
          <div className="tracked-metadata-list">
            {trackedMetadataKeys.map((key) => (
              <span key={key} className="tracked-metadata-token">
                {key}
                <button
                  type="button"
                  className="secondary"
                  disabled={!canRescan || metadataKeySaving}
                  onClick={async () => {
                    setMetadataKeySaving(true);
                    setMetadataKeyError("");
                    try {
                      await onRemoveTrackedMetadataKey(key);
                    } catch (error) {
                      setMetadataKeyError(error instanceof Error ? error.message : "메타데이터 키를 삭제하지 못했습니다.");
                    } finally {
                      setMetadataKeySaving(false);
                    }
                  }}
                >
                  삭제
                </button>
              </span>
            ))}
          </div>
        ) : (
          <p className="empty-inline">아직 등록된 관리자 지정 메타데이터 키가 없습니다.</p>
        )}
      </section>

      <div className="admin-grid">
        <FacetList title="상태별 이미지" items={facets?.status_counts ?? []} mapKey={statusLabel} />
        <FacetList title="주요 디렉터리" items={facets?.directory_counts ?? []} />
        <FacetList title="자주 발견된 메타데이터 키" items={facets?.common_metadata_keys ?? []} />
      </div>
    </main>
  );
}
