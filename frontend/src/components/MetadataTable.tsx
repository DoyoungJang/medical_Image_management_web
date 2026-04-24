import { flattenMetadata } from "../utils/format";

interface MetadataTableProps {
  metadata: Record<string, unknown>;
}

export function MetadataTable({ metadata }: MetadataTableProps) {
  const rows = flattenMetadata(metadata);

  return (
    <div className="metadata-table">
      <div className="metadata-table-head">
        <span>키</span>
        <span>값</span>
      </div>
      {rows.map((row) => (
        <div key={`${row.key}-${row.value}`} className="metadata-row">
          <span>{row.key}</span>
          <span>{row.value}</span>
        </div>
      ))}
    </div>
  );
}

