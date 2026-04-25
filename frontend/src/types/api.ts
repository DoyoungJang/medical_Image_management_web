export interface PublicConfig {
  app_name: string;
  auth_enabled: boolean;
  public_show_absolute_path: boolean;
  supported_image_extensions: string[];
  default_page_size: number;
  max_page_size: number;
  thumbnail_default_size: number;
  thumbnail_max_size: number;
}

export interface SessionResponse {
  authenticated: boolean;
  username?: string | null;
  is_admin: boolean;
}

export interface BreadcrumbItem {
  name: string;
  path: string;
}

export interface FolderNode {
  name: string;
  path: string;
  direct_file_count: number;
  descendant_file_count: number;
}

export interface MetadataSummaryItem {
  key: string;
  value: string;
}

export interface ImageSummary {
  id: number;
  filename: string;
  relative_path: string;
  directory: string;
  extension: string;
  file_size_bytes: number;
  modified_time: string;
  width: number | null;
  height: number | null;
  status: string;
  has_alpha: boolean | null;
  metadata_summary: MetadataSummaryItem[];
}

export interface ImageDetail extends ImageSummary {
  format: string | null;
  mode: string | null;
  bit_depth: number | null;
  color_type: string | null;
  dpi_x: number | null;
  dpi_y: number | null;
  error_message: string | null;
  metadata: Record<string, unknown>;
  absolute_path?: string | null;
}

export interface TreeResponse {
  current_path: string;
  breadcrumbs: BreadcrumbItem[];
  folders: FolderNode[];
  files: ImageSummary[];
}

export interface ImageListResponse {
  items: ImageSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface FacetCount {
  key: string;
  count: number;
}

export interface MetadataFacetsResponse {
  status_counts: FacetCount[];
  directory_counts: FacetCount[];
  common_metadata_keys: FacetCount[];
}

export interface MetadataKeysResponse {
  keys: string[];
}

export interface IndexStatusResponse {
  scanning: boolean;
  last_started_at?: string | null;
  last_finished_at?: string | null;
  last_result?: Record<string, unknown> | null;
  total_images: number;
  active_images: number;
  missing_images: number;
}

export interface SearchFilters {
  q: string;
  directory: string;
  widthMin: string;
  widthMax: string;
  heightMin: string;
  heightMax: string;
  sizeMin: string;
  sizeMax: string;
  modifiedFrom: string;
  modifiedTo: string;
  metadataKey: string;
  metadataValue: string;
  hasAlpha: "" | "true" | "false";
  status: string;
  sort: "filename" | "path" | "file_size" | "modified_time" | "width" | "height";
  order: "asc" | "desc";
  page: number;
  pageSize: number;
}
