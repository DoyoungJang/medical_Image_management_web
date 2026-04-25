import type { FolderNode, TreeResponse } from "../types/api";

interface FolderTreeProps {
  treeCache: Record<string, TreeResponse | undefined>;
  selectedPath: string;
  expandedPaths: Set<string>;
  onSelect: (path: string) => void;
  onToggle: (path: string) => void;
}

function FolderBranch({
  folder,
  depth,
  treeCache,
  selectedPath,
  expandedPaths,
  onSelect,
  onToggle,
}: {
  folder: FolderNode;
  depth: number;
} & FolderTreeProps) {
  const expanded = expandedPaths.has(folder.path);
  const children = treeCache[folder.path]?.folders ?? [];

  return (
    <div className="folder-branch">
      <div className={`folder-row ${selectedPath === folder.path ? "selected" : ""}`} style={{ paddingLeft: `${depth * 14 + 12}px` }}>
        <button className="folder-toggle-button secondary" onClick={() => onToggle(folder.path)}>
          {expanded ? "▾" : "▸"}
        </button>
        <button className="folder-button" onClick={() => onSelect(folder.path)}>
          <span className="folder-name">{folder.name}</span>
          <span className="folder-count">{folder.descendant_file_count}</span>
        </button>
      </div>
      {expanded &&
        children.map((child) => (
          <FolderBranch
            key={child.path}
            folder={child}
            depth={depth + 1}
            treeCache={treeCache}
            selectedPath={selectedPath}
            expandedPaths={expandedPaths}
            onSelect={onSelect}
            onToggle={onToggle}
          />
        ))}
    </div>
  );
}

export function FolderTree({ treeCache, selectedPath, expandedPaths, onSelect, onToggle }: FolderTreeProps) {
  const root = treeCache[""];
  const rootTotalCount =
    (root?.files.length ?? 0) + (root?.folders.reduce((total, folder) => total + folder.descendant_file_count, 0) ?? 0);
  const rootIsEmpty = root !== undefined && root.files.length === 0 && root.folders.length === 0;

  return (
    <div className="panel tree-panel">
      <div className="panel-header">
        <h2>폴더 트리</h2>
        <p>이미지 루트 기준 상대 경로만 표시됩니다.</p>
      </div>
      <div className={`folder-row root ${selectedPath === "" ? "selected" : ""}`}>
        <button className="folder-toggle-button secondary" onClick={() => onToggle("")}>
          {expandedPaths.has("") ? "▾" : "▸"}
        </button>
        <button className="folder-button" onClick={() => onSelect("")}>
          <span className="folder-name">루트</span>
          <span className="folder-count">{rootTotalCount}</span>
        </button>
      </div>
      {rootIsEmpty ? (
        <div className="tree-empty-state">
          인덱싱된 이미지가 없습니다. PNG, JPG, JPEG, BMP를 추가한 뒤 관리자 화면에서 수동 재스캔을 실행해 주세요.
        </div>
      ) : null}
      <div className="folder-list">
        {expandedPaths.has("") &&
          (root?.folders ?? []).map((folder) => (
            <FolderBranch
              key={folder.path}
              folder={folder}
              depth={1}
              treeCache={treeCache}
              selectedPath={selectedPath}
              expandedPaths={expandedPaths}
              onSelect={onSelect}
              onToggle={onToggle}
            />
          ))}
      </div>
    </div>
  );
}
