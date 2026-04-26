import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";

import { AdminPage } from "./components/AdminPage";
import { AuthGate } from "./components/AuthGate";
import { FolderTree } from "./components/FolderTree";
import { ImageDetailDrawer } from "./components/ImageDetailDrawer";
import { ImageGrid } from "./components/ImageGrid";
import { SearchBar } from "./components/SearchBar";
import { useDebouncedValue } from "./hooks/useDebouncedValue";
import type {
  AdminImageRootResponse,
  ImageDetail,
  ImageListResponse,
  IndexStatusResponse,
  MetadataFacetsResponse,
  PublicConfig,
  SearchFilters,
  SessionResponse,
  TreeResponse,
} from "./types/api";
import {
  addTrackedMetadataKey,
  fetchAdminImageRoot,
  fetchFacets,
  fetchImageDetail,
  fetchImages,
  fetchIndexStatus,
  fetchMetadataKeys,
  fetchPublicConfig,
  fetchSession,
  fetchTree,
  fetchTrackedMetadataKeys,
  login,
  logout,
  removeTrackedMetadataKey,
  triggerFolderRescan,
  triggerRescan,
  updateAdminImageRoot,
} from "./utils/api";
import { SORT_LABELS } from "./utils/labels";

const DEFAULT_FILTERS: SearchFilters = {
  q: "",
  directory: "",
  widthMin: "",
  widthMax: "",
  heightMin: "",
  heightMax: "",
  sizeMin: "",
  sizeMax: "",
  modifiedFrom: "",
  modifiedTo: "",
  metadataKey: "",
  metadataValue: "",
  hasAlpha: "",
  status: "",
  sort: "modified_time",
  order: "desc",
  page: 1,
  pageSize: 24,
};

type ViewMode = "browser" | "admin";

function viewFromPath(): ViewMode {
  return window.location.pathname.startsWith("/admin") ? "admin" : "browser";
}

function buildSearchParams(filters: SearchFilters): URLSearchParams {
  const params = new URLSearchParams();
  const mapping: Record<string, string | number> = {
    q: filters.q,
    directory: filters.directory,
    width_min: filters.widthMin,
    width_max: filters.widthMax,
    height_min: filters.heightMin,
    height_max: filters.heightMax,
    size_min: filters.sizeMin,
    size_max: filters.sizeMax,
    modified_from: filters.modifiedFrom,
    modified_to: filters.modifiedTo,
    metadata_key: filters.metadataKey,
    metadata_value: filters.metadataValue,
    has_alpha: filters.hasAlpha,
    status: filters.status,
    sort: filters.sort,
    order: filters.order,
    page: filters.page,
    page_size: filters.pageSize,
  };

  Object.entries(mapping).forEach(([key, value]) => {
    if (value !== "") {
      params.set(key, String(value));
    }
  });

  return params;
}

export default function App() {
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [authLoading, setAuthLoading] = useState(false);
  const [error, setError] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>(viewFromPath);
  const [treeRailExpanded, setTreeRailExpanded] = useState(false);

  const [treeCache, setTreeCache] = useState<Record<string, TreeResponse | undefined>>({});
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set([""]));
  const [selectedPath, setSelectedPath] = useState("");
  const [filters, setFilters] = useState<SearchFilters>(DEFAULT_FILTERS);
  const deferredFilters = useDeferredValue(filters);
  const debouncedFilters = useDebouncedValue(deferredFilters, 200);

  const [images, setImages] = useState<ImageListResponse | null>(null);
  const [imageLoading, setImageLoading] = useState(false);
  const [selectedImageId, setSelectedImageId] = useState<number | null>(null);
  const [selectedImage, setSelectedImage] = useState<ImageDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [fitToScreen, setFitToScreen] = useState(true);

  const [metadataKeys, setMetadataKeys] = useState<string[]>([]);
  const [trackedMetadataKeys, setTrackedMetadataKeys] = useState<string[]>([]);
  const [facets, setFacets] = useState<MetadataFacetsResponse | null>(null);
  const [indexStatus, setIndexStatus] = useState<IndexStatusResponse | null>(null);
  const [imageRootConfig, setImageRootConfig] = useState<AdminImageRootResponse | null>(null);
  const [adminLoading, setAdminLoading] = useState(false);
  const [rescanning, setRescanning] = useState(false);
  const [folderRescanning, setFolderRescanning] = useState(false);
  const [rootUpdating, setRootUpdating] = useState(false);

  const activeTree = treeCache[selectedPath];
  const breadcrumbs = activeTree?.breadcrumbs ?? [{ name: "루트", path: "" }];
  const scanTargetLabel = indexStatus?.current_target_path ? indexStatus.current_target_path : "루트";

  const canBrowse = config !== null && (config.auth_enabled ? session?.authenticated : true);
  const isAdmin = session?.is_admin === true;

  const navigate = (nextView: ViewMode) => {
    setViewMode(nextView);
    const nextPath = nextView === "admin" ? "/admin" : "/";
    window.history.pushState({}, "", nextPath);
  };

  useEffect(() => {
    const handlePopState = () => setViewMode(viewFromPath());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const [configResponse, sessionResponse] = await Promise.all([fetchPublicConfig(), fetchSession()]);
        setConfig(configResponse);
        setSession(sessionResponse);
      } catch (bootstrapError) {
        setError(bootstrapError instanceof Error ? bootstrapError.message : "초기 설정을 불러오지 못했습니다.");
      } finally {
        setInitializing(false);
      }
    };

    void bootstrap();
  }, []);

  useEffect(() => {
    if (canBrowse && viewMode === "admin" && !isAdmin) {
      setViewMode("browser");
      window.history.replaceState({}, "", "/");
    }
  }, [canBrowse, isAdmin, viewMode]);

  useEffect(() => {
    if (!canBrowse) {
      return;
    }
    const loadRoot = async () => {
      const rootTree = await fetchTree("");
      setTreeCache({ "": rootTree });
    };
    void loadRoot();
  }, [canBrowse]);

  useEffect(() => {
    if (!canBrowse) {
      return;
    }

    const loadImages = async () => {
      setImageLoading(true);
      setError("");
      try {
        const params = buildSearchParams(debouncedFilters);
        const imageResponse = await fetchImages(params);
        setImages(imageResponse);
        if (imageResponse.items.length && !imageResponse.items.some((item) => item.id === selectedImageId)) {
          setSelectedImageId(imageResponse.items[0].id);
        }
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "이미지 목록을 불러오지 못했습니다.");
      } finally {
        setImageLoading(false);
      }
    };

    void loadImages();
  }, [canBrowse, debouncedFilters]);

  useEffect(() => {
    if (!canBrowse) {
      return;
    }
    const loadSidebarData = async () => {
      setAdminLoading(true);
      try {
        const [metadataKeysResponse, trackedMetadataKeysResponse, facetsResponse, indexStatusResponse] = await Promise.all([
          fetchMetadataKeys(),
          fetchTrackedMetadataKeys(),
          fetchFacets(new URLSearchParams()),
          fetchIndexStatus(),
        ]);
        setMetadataKeys(metadataKeysResponse.keys);
        setTrackedMetadataKeys(trackedMetadataKeysResponse.keys);
        setFacets(facetsResponse);
        setIndexStatus(indexStatusResponse);
        if (session?.is_admin === true) {
          const rootResponse = await fetchAdminImageRoot();
          setImageRootConfig(rootResponse);
        }
      } catch (sidebarError) {
        setError(sidebarError instanceof Error ? sidebarError.message : "관리자 정보를 불러오지 못했습니다.");
      } finally {
        setAdminLoading(false);
      }
    };
    void loadSidebarData();
  }, [canBrowse, session?.is_admin]);

  useEffect(() => {
    if (!canBrowse) {
      return;
    }

    const interval = window.setInterval(() => {
      void fetchIndexStatus()
        .then(setIndexStatus)
        .catch(() => {
          // Status polling is best-effort; user-triggered actions still surface errors.
        });
    }, 5000);

    return () => window.clearInterval(interval);
  }, [canBrowse]);

  useEffect(() => {
    if (!canBrowse || !indexStatus?.last_finished_at) {
      return;
    }

    const refreshAfterScan = async () => {
      try {
        const params = buildSearchParams(filters);
        const [rootTree, currentTree, imageResponse, facetsResponse, metadataKeysResponse] = await Promise.all([
          fetchTree(""),
          fetchTree(selectedPath),
          fetchImages(params),
          fetchFacets(new URLSearchParams()),
          fetchMetadataKeys(),
        ]);
        setTreeCache((previous) => ({ ...previous, "": rootTree, [selectedPath]: currentTree }));
        setImages(imageResponse);
        setFacets(facetsResponse);
        setMetadataKeys(metadataKeysResponse.keys);
      } catch {
        // A scan finishing should not interrupt browsing; explicit actions still surface errors.
      }
    };

    void refreshAfterScan();
  }, [canBrowse, indexStatus?.last_finished_at]);

  useEffect(() => {
    if (!selectedImageId || !canBrowse) {
      setSelectedImage(null);
      return;
    }

    const loadDetail = async () => {
      setDetailLoading(true);
      try {
        const detail = await fetchImageDetail(selectedImageId);
        setSelectedImage(detail);
      } catch (detailError) {
        setError(detailError instanceof Error ? detailError.message : "상세 정보를 불러오지 못했습니다.");
      } finally {
        setDetailLoading(false);
      }
    };

    void loadDetail();
  }, [canBrowse, selectedImageId]);

  const selectedSummary = useMemo(
    () => images?.items.find((item) => item.id === selectedImageId) ?? null,
    [images, selectedImageId],
  );

  useEffect(() => {
    if (selectedSummary?.directory !== undefined && selectedPath !== selectedSummary.directory) {
      setSelectedPath(selectedSummary.directory);
      if (!treeCache[selectedSummary.directory]) {
        void loadTreeNode(selectedSummary.directory).catch((treeError) => {
          setError(treeError instanceof Error ? treeError.message : "폴더 정보를 불러오지 못했습니다.");
        });
      }
    }
  }, [selectedPath, selectedSummary, treeCache]);

  const handleLogin = async (username: string, password: string) => {
    setAuthLoading(true);
    setError("");
    try {
      const sessionResponse = await login(username, password);
      setSession(sessionResponse);
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "로그인에 실패했습니다.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    setSession({ authenticated: false, is_admin: false });
    setSelectedImageId(null);
    setImageRootConfig(null);
    navigate("browser");
  };

  const loadTreeNode = async (path: string) => {
    const response = await fetchTree(path);
    setTreeCache((previous) => ({ ...previous, [path]: response }));
  };

  const handleFolderSelect = (path: string) => {
    startTransition(() => {
      setSelectedPath(path);
      setFilters((current) => ({ ...current, directory: path, page: 1 }));
    });
    if (!treeCache[path]) {
      void loadTreeNode(path).catch((treeError) => {
        setError(treeError instanceof Error ? treeError.message : "폴더를 불러오지 못했습니다.");
      });
    }
  };

  const handleToggleFolder = (path: string) => {
    setExpandedPaths((current) => {
      const next = new Set(current);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
    if (!treeCache[path]) {
      void loadTreeNode(path).catch((treeError) => {
        setError(treeError instanceof Error ? treeError.message : "하위 폴더를 불러오지 못했습니다.");
      });
    }
  };

  const handleRescan = async () => {
    setRescanning(true);
    try {
      await triggerRescan();
      const refreshedStatus = await fetchIndexStatus();
      setIndexStatus(refreshedStatus);
    } catch (rescanError) {
      setError(rescanError instanceof Error ? rescanError.message : "재스캔 요청에 실패했습니다.");
    } finally {
      setRescanning(false);
    }
  };

  const handleFolderRescan = async () => {
    setFolderRescanning(true);
    setError("");
    try {
      await triggerFolderRescan(selectedPath);
      const refreshedStatus = await fetchIndexStatus();
      setIndexStatus(refreshedStatus);
    } catch (scanError) {
      setError(scanError instanceof Error ? scanError.message : "현재 폴더 재스캔 요청에 실패했습니다.");
    } finally {
      setFolderRescanning(false);
    }
  };

  const resetBrowserStateAfterRootChange = () => {
    setTreeCache({});
    setExpandedPaths(new Set([""]));
    setSelectedPath("");
    setSelectedImageId(null);
    setSelectedImage(null);
    setImages(null);
    setFilters((current) => ({ ...DEFAULT_FILTERS, pageSize: current.pageSize }));
  };

  const handleUpdateImageRoot = async (rootDir: string) => {
    setRootUpdating(true);
    setError("");
    try {
      const response = await updateAdminImageRoot(rootDir);
      setImageRootConfig(response);
      resetBrowserStateAfterRootChange();
      const refreshedStatus = await fetchIndexStatus();
      setIndexStatus(refreshedStatus);
      const rootTree = await fetchTree("");
      setTreeCache({ "": rootTree });
      return response;
    } catch (rootError) {
      setError(rootError instanceof Error ? rootError.message : "이미지 루트 경로 변경에 실패했습니다.");
      throw rootError;
    } finally {
      setRootUpdating(false);
    }
  };

  const refreshCurrentImages = async () => {
    const params = buildSearchParams(filters);
    const imageResponse = await fetchImages(params);
    setImages(imageResponse);
    if (selectedImageId) {
      const detail = await fetchImageDetail(selectedImageId);
      setSelectedImage(detail);
    }
  };

  const handleAddTrackedMetadataKey = async (key: string) => {
    const response = await addTrackedMetadataKey(key);
    setTrackedMetadataKeys(response.keys);
    await refreshCurrentImages();
  };

  const handleRemoveTrackedMetadataKey = async (key: string) => {
    const response = await removeTrackedMetadataKey(key);
    setTrackedMetadataKeys(response.keys);
    await refreshCurrentImages();
  };

  const handlePageSizeChange = (rawValue: string) => {
    const parsedValue = Number(rawValue);
    const nextPageSize = Math.min(config?.max_page_size ?? 100, Math.max(1, Number.isFinite(parsedValue) ? parsedValue : 1));
    setFilters((current) => ({ ...current, pageSize: nextPageSize, page: 1 }));
  };

  if (initializing) {
    return <div className="app-loading">초기 설정을 불러오는 중입니다.</div>;
  }

  if (!config) {
    return <div className="app-loading">공개 설정을 불러오지 못했습니다.</div>;
  }

  if (config.auth_enabled && !session?.authenticated) {
    return <AuthGate loading={authLoading} error={error} onLogin={handleLogin} />;
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">사내 도구</p>
          <h1>{config.app_name}</h1>
          <p className="muted">PNG, JPG/JPEG, BMP, GIF, TIFF, WEBP 등 이미지 탐색과 메타데이터 검색을 안전하게 처리합니다.</p>
        </div>
        <div className="header-actions">
          <div className="view-tabs" role="tablist" aria-label="주요 화면">
            <button className={viewMode === "browser" ? "active" : "secondary"} onClick={() => navigate("browser")}>
              탐색
            </button>
            {isAdmin ? (
              <button className={viewMode === "admin" ? "active" : "secondary"} onClick={() => navigate("admin")}>
                관리자
              </button>
            ) : null}
          </div>
          <span className="chip">현재 폴더: {selectedPath || "루트"}</span>
          <button className="secondary" onClick={() => void handleLogout()}>
            로그아웃
          </button>
        </div>
      </header>

      {error ? <div className="global-error">{error}</div> : null}

      {viewMode === "browser" || !isAdmin ? (
        <div className={`app-layout ${treeRailExpanded ? "tree-expanded" : ""}`}>
          <aside
            className="left-rail"
            onMouseEnter={() => setTreeRailExpanded(true)}
            onMouseLeave={() => setTreeRailExpanded(false)}
            onFocusCapture={() => setTreeRailExpanded(true)}
            onBlurCapture={(event) => {
              if (!event.relatedTarget || !event.currentTarget.contains(event.relatedTarget as Node)) {
                setTreeRailExpanded(false);
              }
            }}
          >
            <FolderTree
              treeCache={treeCache}
              selectedPath={selectedPath}
              expandedPaths={expandedPaths}
              onSelect={handleFolderSelect}
              onToggle={handleToggleFolder}
            />
          </aside>

          <main className="main-content">
            <SearchBar
              filters={filters}
              metadataKeys={metadataKeys}
              onChange={(patch) => setFilters((current) => ({ ...current, ...patch }))}
              onSubmit={() => setFilters((current) => ({ ...current, page: 1 }))}
              onReset={() => {
                setFilters({ ...DEFAULT_FILTERS, directory: selectedPath });
              }}
            />

            <div className="content-header">
              <div>
                <h2>검색 결과</h2>
                <p className="muted">
                  총 {images?.total ?? 0}개 / 페이지 {images?.page ?? 1} / 정렬: {SORT_LABELS[filters.sort]}
                </p>
              </div>
              <div className="pagination">
                {indexStatus?.scanning ? <span className="scan-badge">스캔 진행 중: {scanTargetLabel}</span> : null}
                <button
                  className="secondary"
                  disabled={folderRescanning || Boolean(indexStatus?.scanning)}
                  onClick={() => void handleFolderRescan()}
                >
                  {folderRescanning
                    ? "폴더 스캔 요청 중"
                    : indexStatus?.scanning
                      ? "스캔 진행 중"
                      : "현재 폴더 스캔"}
                </button>
                <label className="page-size-control">
                  <span>표시 개수</span>
                  <input
                    type="number"
                    min={1}
                    max={config.max_page_size}
                    value={filters.pageSize}
                    onChange={(event) => handlePageSizeChange(event.target.value)}
                  />
                  <small>최대 {config.max_page_size}</small>
                </label>
                <button
                  className="secondary"
                  disabled={(filters.page ?? 1) <= 1}
                  onClick={() => setFilters((current) => ({ ...current, page: Math.max(1, current.page - 1) }))}
                >
                  이전
                </button>
                <button
                  className="secondary"
                  disabled={!images || images.items.length < filters.pageSize}
                  onClick={() => setFilters((current) => ({ ...current, page: current.page + 1 }))}
                >
                  다음
                </button>
              </div>
            </div>

            <ImageGrid
              items={images?.items ?? []}
              loading={imageLoading}
              selectedImageId={selectedImageId}
              thumbnailSize={config.thumbnail_default_size}
              onSelect={(imageId) => {
                setSelectedImageId(imageId);
                setZoom(1);
                setFitToScreen(true);
              }}
            />
          </main>

          <ImageDetailDrawer
            image={selectedImage}
            loading={detailLoading}
            breadcrumbs={breadcrumbs}
            zoom={zoom}
            fitToScreen={fitToScreen}
            onClose={() => setSelectedImageId(null)}
            onZoomChange={setZoom}
            onToggleFit={() => setFitToScreen((current) => !current)}
          />
        </div>
      ) : (
        <AdminPage
          config={config}
          indexStatus={indexStatus}
          facets={facets}
          loading={adminLoading}
          rescanning={rescanning}
          canRescan={isAdmin}
          metadataKeys={metadataKeys}
          trackedMetadataKeys={trackedMetadataKeys}
          imageRootConfig={imageRootConfig}
          rootUpdating={rootUpdating}
          onRescan={handleRescan}
          onUpdateImageRoot={handleUpdateImageRoot}
          onAddTrackedMetadataKey={handleAddTrackedMetadataKey}
          onRemoveTrackedMetadataKey={handleRemoveTrackedMetadataKey}
        />
      )}
    </div>
  );
}
