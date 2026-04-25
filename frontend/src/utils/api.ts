import type {
  ImageDetail,
  ImageListResponse,
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

export async function fetchIndexStatus(): Promise<IndexStatusResponse> {
  return request<IndexStatusResponse>("/admin/index-status");
}

export async function triggerRescan(): Promise<{ status: string }> {
  return request<{ status: string }>("/admin/rescan", { method: "POST" });
}

export function imageThumbnailUrl(imageId: number, size: number): string {
  const params = new URLSearchParams({ size: String(size) });
  return `${API_BASE}/images/${imageId}/thumbnail?${params.toString()}`;
}

export function imageFileUrl(imageId: number): string {
  return `${API_BASE}/images/${imageId}/file`;
}
