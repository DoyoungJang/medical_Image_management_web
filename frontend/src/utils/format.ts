export function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(value < 10 ? 1 : 0)} ${units[index]}`;
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function flattenMetadata(
  input: Record<string, unknown>,
  prefix = "",
): Array<{ key: string; value: string }> {
  return Object.entries(input).flatMap(([key, value]) => {
    const nextKey = prefix ? `${prefix}.${key}` : key;
    if (value === null || value === undefined) {
      return [{ key: nextKey, value: "-" }];
    }
    if (typeof value === "object" && !Array.isArray(value)) {
      return flattenMetadata(value as Record<string, unknown>, nextKey);
    }
    if (Array.isArray(value)) {
      return value.map((item, index) => ({
        key: `${nextKey}[${index}]`,
        value: typeof item === "object" ? JSON.stringify(item) : String(item),
      }));
    }
    return [{ key: nextKey, value: String(value) }];
  });
}

