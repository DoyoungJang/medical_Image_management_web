const HIDDEN_METADATA_KEYS = new Set([
  "pillow_info.jfif_density[1]",
  "pillow_info.jfif_unit",
  "pillow_info.jfif_version[0]",
  "pillow_info.jfif_version[1]",
  "pillow_info.xmp",
  "relative_path",
  "textual_metadata.xmp[0]",
  "icc_profile.present",
  "icc_profile.summary",
  "dpi.x",
  "dpi.y",
  "exif_present",
]);

export function shouldShowMetadataRow(key: string): boolean {
  return !HIDDEN_METADATA_KEYS.has(key);
}
