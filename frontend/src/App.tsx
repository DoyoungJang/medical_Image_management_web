import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";

import { AdminPanel } from "./components/AdminPanel";
import { AuthGate } from "./components/AuthGate";
import { FolderTree } from "./components/FolderTree";
import { ImageDetailDrawer } from "./components/ImageDetailDrawer";
import { ImageGrid } from "./components/ImageGrid";
import { SearchBar } from "./components/SearchBar";
import { useDebouncedValue } from "./hooks/useDebouncedValue";
import type {
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
  fetchFacets,
  fetchImageDetail,
  fetchImages,
  fetchIndexStatus,
  fetchMetadataKeys,
  fetchPublicConfig,
  fetchSession,
  fetchTree,
  login,
  logout,
  triggerRescan,
} from "./utils/api";

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
  const [facets, setFacets] = useState<MetadataFacetsResponse | null>(null);
  const [indexStatus, setIndexStatus] = useState<IndexStatusResponse | null>(null);
  const [adminLoading, setAdminLoading] = useState(false);
  const [rescanning, setRescanning] = useState(false);

  const activeTree = treeCache[selectedPath];
  const breadcrumbs = activeTree?.breadcrumbs ?? [{ name: "루트", path: "" }];

  const canBrowse = config !== null && (config.auth_enabled ? session?.authenticated : true);

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
        const [metadataKeysResponse, facetsResponse, indexStatusResponse] = await Promise.all([
          fetchMetadataKeys(),
          fetchFacets(buildSearchParams(debouncedFilters)),
          fetchIndexStatus(),
        ]);
        setMetadataKeys(metadataKeysResponse.keys);
        setFacets(facetsResponse);
        setIndexStatus(indexStatusResponse);
      } catch (sidebarError) {
        setError(sidebarError instanceof Error ? sidebarError.message : "보조 정보를 불러오지 못했습니다.");
      } finally {
        setAdminLoading(false);
      }
    };
    void loadSidebarData();
  }, [canBrowse, debouncedFilters]);

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
    }
  }, [selectedPath, selectedSummary]);

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
    setSession({ authenticated: false });
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

  if (initializing) {
    return <div className="app-loading">초기 설정을 불러오는 중입니다...</div>;
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
          <p className="eyebrow">Internal Tool</p>
          <h1>{config.app_name}</h1>
          <p className="muted">PNG 폴더 탐색, 메타데이터 인덱싱, 조건 검색을 하나의 화면에서 처리합니다.</p>
        </div>
        <div className="header-actions">
          <span className="chip">현재 폴더: {selectedPath || "루트"}</span>
          <button className="secondary" onClick={() => void handleLogout()}>
            로그아웃
          </button>
        </div>
      </header>

      {error ? <div className="global-error">{error}</div> : null}

      <div className="app-layout">
        <aside className="left-rail">
          <FolderTree
            treeCache={treeCache}
            selectedPath={selectedPath}
            expandedPaths={expandedPaths}
            onSelect={handleFolderSelect}
            onToggle={handleToggleFolder}
          />
          <AdminPanel indexStatus={indexStatus} facets={facets} loading={adminLoading} rescanning={rescanning} onRescan={handleRescan} />
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
                총 {images?.total ?? 0}개 / 페이지 {images?.page ?? 1}
              </p>
            </div>
            <div className="pagination">
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
    </div>
  );
}
