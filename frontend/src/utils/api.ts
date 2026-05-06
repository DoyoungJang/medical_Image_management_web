import type {
  AdminImageRootResponse,
  AdminExportRootResponse,
  AdminSignupCodeResponse,
  ExportFilteredImagesResponse,
  ExportStorageBackend,
  ExportStructureMode,
  ImageDetail,
  ImageListResponse,
  ImageRescanResponse,
  IndexStatusResponse,
  MetadataKeysResponse,
  MetadataFacetsResponse,
  PublicConfig,
  SessionResponse,
  TrackedMetadataKeysResponse,
  TreeResponse,
} from "../types/api";
import { translateServerMessage } from "./labels";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const message = translateServerMessage(payload?.detail ?? `요청 실패 (${response.status})`);
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function fetchPublicConfig(): Promise<PublicConfig> {
  return request<PublicConfig>("/config/public");
}

export async function fetchSession(): Promise<SessionResponse> {
  return request<SessionResponse>("/auth/session");
}

export async function login(username: string, password: string): Promise<SessionResponse> {
  return request<SessionResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function register(username: string, password: string, signupCode: string): Promise<SessionResponse> {
  return request<SessionResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password, signup_code: signupCode }),
  });
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<SessionResponse> {
  return request<SessionResponse>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

export async function logout(): Promise<SessionResponse> {
  return request<SessionResponse>("/auth/logout", { method: "POST" });
}

export async function fetchTree(path = ""): Promise<TreeResponse> {
  const params = new URLSearchParams();
  if (path) {
    params.set("path", path);
  }
  return request<TreeResponse>(`/tree?${params.toString()}`);
}

export async function fetchImages(params: URLSearchParams): Promise<ImageListResponse> {
  return request<ImageListResponse>(`/images?${params.toString()}`);
}

export async function fetchImageDetail(imageId: number): Promise<ImageDetail> {
  return request<ImageDetail>(`/images/${imageId}`);
}

export async function rescanImage(imageId: number): Promise<ImageRescanResponse> {
  return request<ImageRescanResponse>(`/images/${imageId}/rescan`, { method: "POST" });
}

export async function fetchFacets(params: URLSearchParams): Promise<MetadataFacetsResponse> {
  return request<MetadataFacetsResponse>(`/metadata/facets?${params.toString()}`);
}

export async function fetchMetadataKeys(): Promise<MetadataKeysResponse> {
  return request<MetadataKeysResponse>("/metadata/keys");
}

export async function fetchTrackedMetadataKeys(): Promise<TrackedMetadataKeysResponse> {
  return request<TrackedMetadataKeysResponse>("/metadata/tracked-keys");
}

export async function addTrackedMetadataKey(key: string): Promise<TrackedMetadataKeysResponse> {
  return request<TrackedMetadataKeysResponse>("/admin/tracked-metadata-keys", {
    method: "POST",
    body: JSON.stringify({ key }),
  });
}

export async function removeTrackedMetadataKey(key: string): Promise<TrackedMetadataKeysResponse> {
  return request<TrackedMetadataKeysResponse>("/admin/tracked-metadata-keys", {
    method: "DELETE",
    body: JSON.stringify({ key }),
  });
}

export async function fetchAdminImageRoot(): Promise<AdminImageRootResponse> {
  return request<AdminImageRootResponse>("/admin/root");
}

export async function updateAdminImageRoot(rootDir: string): Promise<AdminImageRootResponse> {
  return request<AdminImageRootResponse>("/admin/root", {
    method: "PATCH",
    body: JSON.stringify({ root_dir: rootDir, rescan: true }),
  });
}

export async function fetchAdminExportRoot(): Promise<AdminExportRootResponse> {
  return request<AdminExportRootResponse>("/admin/export-root");
}

export async function updateAdminExportRoot(rootDir: string): Promise<AdminExportRootResponse> {
  return request<AdminExportRootResponse>("/admin/export-root", {
    method: "PATCH",
    body: JSON.stringify({ root_dir: rootDir }),
  });
}

export async function fetchAdminSignupCode(): Promise<AdminSignupCodeResponse> {
  return request<AdminSignupCodeResponse>("/admin/signup-code");
}

export async function updateAdminSignupCode(signupCode: string): Promise<AdminSignupCodeResponse> {
  return request<AdminSignupCodeResponse>("/admin/signup-code", {
    method: "PATCH",
    body: JSON.stringify({ signup_code: signupCode }),
  });
}

export async function fetchIndexStatus(): Promise<IndexStatusResponse> {
  return request<IndexStatusResponse>("/admin/index-status");
}

export async function triggerRescan(): Promise<{ status: string }> {
  return request<{ status: string }>("/admin/rescan", { method: "POST" });
}

export async function triggerFolderRescan(path: string): Promise<{ status: string; path: string }> {
  return request<{ status: string; path: string }>("/folders/rescan", {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}

export async function exportFilteredImages(
  destinationDir: string,
  params: URLSearchParams,
  structureMode: ExportStructureMode,
  storageBackend: ExportStorageBackend,
  imageIds: number[] | null = null,
): Promise<ExportFilteredImagesResponse> {
  const payload: Record<string, string | boolean | number[] | Array<{ key: string; value: string }> | null> = {
    destination_dir: destinationDir,
    structure_mode: structureMode,
    storage_backend: storageBackend,
  };
  if (imageIds?.length) {
    payload.image_ids = imageIds;
  }
  params.forEach((value, key) => {
    if (key === "page" || key === "page_size") {
      return;
    }
    if (key === "status") {
      payload.status_filter = value;
      return;
    }
    if (key === "has_alpha") {
      payload.has_alpha = value === "true";
      return;
    }
    if (key === "metadata_key" || key === "metadata_value") {
      return;
    }
    payload[key] = value;
  });
  const metadataKeys = params.getAll("metadata_key");
  const metadataValues = params.getAll("metadata_value");
  const metadataFilters = metadataKeys
    .map((key, index) => ({ key, value: metadataValues[index] ?? "" }))
    .filter((item) => item.key.trim());
  if (metadataFilters.length) {
    payload.metadata_filters = metadataFilters;
  }
  return request<ExportFilteredImagesResponse>("/images/export-filtered", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function imageThumbnailUrl(imageId: number, size: number): string {
  const params = new URLSearchParams({ size: String(size) });
  return `${API_BASE}/images/${imageId}/thumbnail?${params.toString()}`;
}

export function imageFileUrl(imageId: number): string {
  return `${API_BASE}/images/${imageId}/file`;
}
