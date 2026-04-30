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
  AdminExportRootResponse,
  ExportStorageBackend,
  ExportStructureMode,
  ImageDetail,
  ImageListResponse,
  ImageSummary,
  ImageViewMode,
  IndexStatusResponse,
  MetadataFacetsResponse,
  PublicConfig,
  MetadataFilter,
  SearchFilters,
  SessionResponse,
  TreeResponse,
} from "./types/api";
import {
  addTrackedMetadataKey,
  exportFilteredImages,
  fetchAdminExportRoot,
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
  rescanImage,
  triggerFolderRescan,
  triggerRescan,
  imageFileUrl,
  updateAdminExportRoot,
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
  metadataFilters: [{ key: "", value: "" }],
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
  filters.metadataFilters.forEach((metadataFilter) => {
    if (!metadataFilter.key.trim()) {
      return;
    }
    params.append("metadata_key", metadataFilter.key.trim());
    params.append("metadata_value", metadataFilter.value.trim());
  });

  return params;
}

type FileSystemDirectoryHandleLike = {
  getDirectoryHandle: (name: string, options?: { create?: boolean }) => Promise<FileSystemDirectoryHandleLike>;
  getFileHandle: (name: string, options?: { create?: boolean }) => Promise<{
    createWritable: () => Promise<{
      write: (data: Blob) => Promise<void>;
      close: () => Promise<void>;
    }>;
  }>;
};

type WindowWithDirectoryPicker = Window & {
  showDirectoryPicker?: () => Promise<FileSystemDirectoryHandleLike>;
};

function sanitizePathSegment(segment: string): string {
  return segment.replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_").trim() || "unnamed";
}

function uniqueFilename(filename: string, usedNames: Set<string>): string {
  const safeName = sanitizePathSegment(filename);
  const dotIndex = safeName.lastIndexOf(".");
  const stem = dotIndex > 0 ? safeName.slice(0, dotIndex) : safeName;
  const extension = dotIndex > 0 ? safeName.slice(dotIndex) : "";
  let candidate = safeName;
  let index = 2;
  while (usedNames.has(candidate.toLowerCase())) {
    candidate = `${stem}_${index}${extension}`;
    index += 1;
  }
  usedNames.add(candidate.toLowerCase());
  return candidate;
}

async function resolveDirectoryHandle(
  rootHandle: FileSystemDirectoryHandleLike,
  relativePath: string,
): Promise<FileSystemDirectoryHandleLike> {
  const directoryParts = relativePath.split("/").slice(0, -1).filter(Boolean).map(sanitizePathSegment);
  let currentHandle = rootHandle;
  for (const part of directoryParts) {
    currentHandle = await currentHandle.getDirectoryHandle(part, { create: true });
  }
  return currentHandle;
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
  const [selectedImageIds, setSelectedImageIds] = useState<Set<number>>(new Set());
  const [selectionAnchorId, setSelectionAnchorId] = useState<number | null>(null);
  const [selectedImage, setSelectedImage] = useState<ImageDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [fitToScreen, setFitToScreen] = useState(true);
  const [imageViewMode, setImageViewMode] = useState<ImageViewMode>("grid");

  const [metadataKeys, setMetadataKeys] = useState<string[]>([]);
  const [trackedMetadataKeys, setTrackedMetadataKeys] = useState<string[]>([]);
  const [facets, setFacets] = useState<MetadataFacetsResponse | null>(null);
  const [indexStatus, setIndexStatus] = useState<IndexStatusResponse | null>(null);
  const [imageRootConfig, setImageRootConfig] = useState<AdminImageRootResponse | null>(null);
  const [exportRootConfig, setExportRootConfig] = useState<AdminExportRootResponse | null>(null);
  const [adminLoading, setAdminLoading] = useState(false);
  const [rescanning, setRescanning] = useState(false);
  const [folderRescanning, setFolderRescanning] = useState(false);
  const [rootUpdating, setRootUpdating] = useState(false);
  const [exportRootUpdating, setExportRootUpdating] = useState(false);
  const [imageRescanning, setImageRescanning] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportDir, setExportDir] = useState("");
  const [exportStructureMode, setExportStructureMode] = useState<ExportStructureMode>("preserve");
  const [exportStorageBackend, setExportStorageBackend] = useState<ExportStorageBackend>("local");
  const [exportMessage, setExportMessage] = useState("");

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
    if (config?.export_storage_backend) {
      setExportStorageBackend(config.export_storage_backend);
    }
  }, [config?.export_storage_backend]);

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
        setSelectedImageIds((current) => {
          const visibleIds = new Set(imageResponse.items.map((item) => item.id));
          return new Set([...current].filter((imageId) => visibleIds.has(imageId)));
        });
        setSelectionAnchorId((current) => (imageResponse.items.some((item) => item.id === current) ? current : null));
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
          const [rootResponse, exportRootResponse] = await Promise.all([fetchAdminImageRoot(), fetchAdminExportRoot()]);
          setImageRootConfig(rootResponse);
          setExportRootConfig(exportRootResponse);
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

    let interval: number | undefined;
    const pollStatus = () => {
      void fetchIndexStatus()
        .then(setIndexStatus)
        .catch(() => {
          // Status polling is best-effort; user-triggered actions still surface errors.
        });
    };
    const initialDelay = 1000 + Math.floor(Math.random() * 2000);
    const timeout = window.setTimeout(() => {
      pollStatus();
      interval = window.setInterval(pollStatus, 5000 + Math.floor(Math.random() * 1000));
    }, initialDelay);

    return () => {
      window.clearTimeout(timeout);
      if (interval !== undefined) {
        window.clearInterval(interval);
      }
    };
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
    setExportRootConfig(null);
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

  const handleImageRescan = async (imageId: number) => {
    setImageRescanning(true);
    setError("");
    try {
      const response = await rescanImage(imageId);
      setSelectedImage(response.image);
      await refreshCurrentImages();
      const refreshedStatus = await fetchIndexStatus();
      setIndexStatus(refreshedStatus);
    } catch (scanError) {
      setError(scanError instanceof Error ? scanError.message : "이미지 재스캔에 실패했습니다.");
    } finally {
      setImageRescanning(false);
    }
  };

  const visibleItems = images?.items ?? [];
  const selectedVisibleItems = visibleItems.filter((item) => selectedImageIds.has(item.id));
  const exportTargetItems = selectedVisibleItems.length ? selectedVisibleItems : visibleItems;

  const selectRangeTo = (imageId: number, currentSelection: Set<number>) => {
    const anchorId = selectionAnchorId ?? selectedImageId ?? imageId;
    const anchorIndex = visibleItems.findIndex((item) => item.id === anchorId);
    const targetIndex = visibleItems.findIndex((item) => item.id === imageId);
    if (anchorIndex < 0 || targetIndex < 0) {
      currentSelection.add(imageId);
      return currentSelection;
    }
    const [startIndex, endIndex] =
      anchorIndex < targetIndex ? [anchorIndex, targetIndex] : [targetIndex, anchorIndex];
    visibleItems.slice(startIndex, endIndex + 1).forEach((item) => currentSelection.add(item.id));
    return currentSelection;
  };

  const handleToggleSelected = (imageId: number, shiftKey = false) => {
    setSelectedImageIds((current) => {
      const next = new Set(current);
      if (shiftKey) {
        return selectRangeTo(imageId, next);
      }
      if (next.has(imageId)) {
        next.delete(imageId);
      } else {
        next.add(imageId);
      }
      return next;
    });
    setSelectionAnchorId(imageId);
  };

  const handleImageSelect = (imageId: number, shiftKey = false) => {
    setSelectedImageId(imageId);
    setZoom(1);
    setFitToScreen(true);
    if (shiftKey) {
      handleToggleSelected(imageId, true);
      return;
    }
    setSelectionAnchorId(imageId);
  };

  const handleSelectAllVisible = () => {
    setSelectedImageIds((current) => {
      const next = new Set(current);
      visibleItems.forEach((item) => next.add(item.id));
      return next;
    });
    if (visibleItems.length) {
      setSelectionAnchorId(visibleItems[0].id);
    }
  };

  const handleClearSelection = () => {
    setSelectedImageIds(new Set());
    setSelectionAnchorId(null);
  };

  const writeLocalImageFile = async (
    rootHandle: FileSystemDirectoryHandleLike,
    item: ImageSummary,
    usedFlatNames: Set<string>,
  ) => {
    const response = await fetch(imageFileUrl(item.id), { credentials: "include" });
    if (!response.ok) {
      throw new Error(`${item.filename} 파일을 내려받지 못했습니다.`);
    }
    const blob = await response.blob();
    const directoryHandle =
      exportStructureMode === "preserve" ? await resolveDirectoryHandle(rootHandle, item.relative_path) : rootHandle;
    const filename =
      exportStructureMode === "preserve"
        ? sanitizePathSegment(item.filename)
        : uniqueFilename(item.filename, usedFlatNames);
    const fileHandle = await directoryHandle.getFileHandle(filename, { create: true });
    const writable = await fileHandle.createWritable();
    await writable.write(blob);
    await writable.close();
  };

  const handleExportLocal = async () => {
    if (!exportTargetItems.length) {
      setError("저장할 이미지가 없습니다.");
      return;
    }
    const picker = (window as WindowWithDirectoryPicker).showDirectoryPicker;
    if (!picker) {
      setError("이 브라우저는 폴더 선택 저장을 지원하지 않습니다. Chrome 또는 Edge에서 다시 시도하세요.");
      return;
    }

    setExporting(true);
    setExportMessage("");
    setError("");
    try {
      const rootHandle = await picker();
      const usedFlatNames = new Set<string>();
      let saved = 0;
      for (const item of exportTargetItems) {
        await writeLocalImageFile(rootHandle, item, usedFlatNames);
        saved += 1;
      }
      setExportMessage(
        `${saved}개 이미지를 선택한 PC 폴더에 저장했습니다. ${
          selectedVisibleItems.length ? "선택한 파일만 저장했습니다." : "현재 표시된 필터 결과를 저장했습니다."
        }`,
      );
    } catch (exportError) {
      if (exportError instanceof DOMException && exportError.name === "AbortError") {
        return;
      }
      setError(exportError instanceof Error ? exportError.message : "PC 폴더로 저장하지 못했습니다.");
    } finally {
      setExporting(false);
    }
  };

  const handleExportFiltered = async () => {
    const destination = exportDir.trim();
    if (!destination) {
      setError("저장할 폴더명을 입력하세요.");
      return;
    }
    setExporting(true);
    setExportMessage("");
    setError("");
    try {
      const selectedIds = selectedVisibleItems.map((item) => item.id);
      const result = await exportFilteredImages(
        destination,
        buildSearchParams(filters),
        exportStructureMode,
        exportStorageBackend,
        selectedIds.length ? selectedIds : null,
      );
      setExportMessage(
        `${result.total_matched}개 중 ${result.copied}개를 서버의 ${result.destination_dir} 폴더에 저장했습니다.${result.skipped ? ` (${result.skipped}개 건너뜀)` : ""}${result.limit_applied ? " 최대 저장 개수 제한이 적용되었습니다." : ""}`,
      );
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "필터 결과 저장에 실패했습니다.");
    } finally {
      setExporting(false);
    }
  };

  const resetBrowserStateAfterRootChange = () => {
    setTreeCache({});
    setExpandedPaths(new Set([""]));
    setSelectedPath("");
    setSelectedImageId(null);
    setSelectedImageIds(new Set());
    setSelectionAnchorId(null);
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

  const handleUpdateExportRoot = async (rootDir: string) => {
    setExportRootUpdating(true);
    setError("");
    try {
      const response = await updateAdminExportRoot(rootDir);
      setExportRootConfig(response);
      return response;
    } catch (rootError) {
      setError(rootError instanceof Error ? rootError.message : "서버 저장 경로 변경에 실패했습니다.");
      throw rootError;
    } finally {
      setExportRootUpdating(false);
    }
  };

  const refreshCurrentImages = async () => {
    const params = buildSearchParams(filters);
    const imageResponse = await fetchImages(params);
    setImages(imageResponse);
    setSelectedImageIds((current) => {
      const visibleIds = new Set(imageResponse.items.map((item) => item.id));
      return new Set([...current].filter((imageId) => visibleIds.has(imageId)));
    });
    setSelectionAnchorId((current) => (imageResponse.items.some((item) => item.id === current) ? current : null));
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
    const nextPageSize = Math.min(config?.max_page_size ?? 1000, Math.max(1, Number.isFinite(parsedValue) ? parsedValue : 1));
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

            <div className="panel result-toolbar">
              <div className="view-tabs" role="tablist" aria-label="이미지 보기 방식">
                <button
                  className={imageViewMode === "grid" ? "active" : "secondary"}
                  onClick={() => setImageViewMode("grid")}
                >
                  카드
                </button>
                <button
                  className={imageViewMode === "imageOnly" ? "active" : "secondary"}
                  onClick={() => setImageViewMode("imageOnly")}
                >
                  이미지만
                </button>
                <button
                  className={imageViewMode === "details" ? "active" : "secondary"}
                  onClick={() => setImageViewMode("details")}
                >
                  자세히
                </button>
              </div>
              <div className="selection-actions">
                <span className="chip">선택 {selectedImageIds.size}개</span>
                <button className="secondary" onClick={handleSelectAllVisible} disabled={!visibleItems.length}>
                  표시된 파일 선택
                </button>
                <button className="secondary" onClick={handleClearSelection} disabled={!selectedImageIds.size}>
                  선택 해제
                </button>
              </div>
            </div>

            <div className="panel export-panel">
              <div>
                <strong>필터 결과 일괄 저장</strong>
                <p className="muted">선택한 파일이 있으면 선택 파일만, 없으면 현재 표시된 필터 결과를 저장합니다.</p>
              </div>
              <label>
                서버 저장 폴더명
                <input
                  value={exportDir}
                  placeholder="예: 2026-04-review"
                  onChange={(event) => setExportDir(event.target.value)}
                />
              </label>
              <label>
                폴더 구조
                <select
                  value={exportStructureMode}
                  onChange={(event) => setExportStructureMode(event.target.value as ExportStructureMode)}
                >
                  <option value="flat">한 폴더에 모두 저장</option>
                  <option value="preserve">원래 폴더 구조 유지</option>
                </select>
              </label>
              <label>
                저장 백엔드
                <select
                  value={exportStorageBackend}
                  onChange={(event) => setExportStorageBackend(event.target.value as ExportStorageBackend)}
                >
                  <option value="local">서버 로컬 폴더</option>
                  <option value="object" disabled={!config.object_storage_configured}>
                    MinIO/lakeFS 오브젝트 스토리지
                  </option>
                </select>
              </label>
              <div className="export-actions">
                <button className="secondary" disabled={exporting || !exportTargetItems.length} onClick={() => void handleExportLocal()}>
                  {exporting ? "저장 중" : "내 PC 폴더 선택 저장"}
                </button>
                <button className="secondary" disabled={exporting || !exportDir.trim()} onClick={() => void handleExportFiltered()}>
                  {exportStorageBackend === "object" ? "MinIO/lakeFS에 저장" : "서버에 저장"}
                </button>
              </div>
              {exportMessage ? <p className="success-inline">{exportMessage}</p> : null}
            </div>

            <ImageGrid
              items={images?.items ?? []}
              loading={imageLoading}
              selectedImageId={selectedImageId}
              selectedImageIds={selectedImageIds}
              thumbnailSize={config.thumbnail_default_size}
              viewMode={imageViewMode}
              onSelect={handleImageSelect}
              onToggleSelected={handleToggleSelected}
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
            rescanning={imageRescanning}
            onRescan={(imageId) => void handleImageRescan(imageId)}
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
          exportRootConfig={exportRootConfig}
          rootUpdating={rootUpdating}
          exportRootUpdating={exportRootUpdating}
          onRescan={handleRescan}
          onUpdateImageRoot={handleUpdateImageRoot}
          onUpdateExportRoot={handleUpdateExportRoot}
          onAddTrackedMetadataKey={handleAddTrackedMetadataKey}
          onRemoveTrackedMetadataKey={handleRemoveTrackedMetadataKey}
        />
      )}
    </div>
  );
}
