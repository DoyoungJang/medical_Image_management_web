import type { MetadataFilter, SearchFilters } from "../types/api";
import { STATUS_LABELS } from "../utils/labels";

interface SearchBarProps {
  filters: SearchFilters;
  metadataKeys: string[];
  onChange: (patch: Partial<SearchFilters>) => void;
  onSubmit: () => void;
  onReset: () => void;
}

function normalizeMetadataFilters(filters: MetadataFilter[]): MetadataFilter[] {
  return filters.length ? filters : [{ key: "", value: "" }];
}

export function SearchBar({ filters, metadataKeys, onChange, onSubmit, onReset }: SearchBarProps) {
  const metadataFilters = normalizeMetadataFilters(filters.metadataFilters);

  const updateMetadataFilter = (index: number, patch: Partial<MetadataFilter>) => {
    const nextFilters = metadataFilters.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item));
    onChange({ metadataFilters: nextFilters, page: 1 });
  };

  const addMetadataFilter = () => {
    onChange({ metadataFilters: [...metadataFilters, { key: "", value: "" }], page: 1 });
  };

  const removeMetadataFilter = (index: number) => {
    const nextFilters = metadataFilters.filter((_item, itemIndex) => itemIndex !== index);
    onChange({ metadataFilters: normalizeMetadataFilters(nextFilters), page: 1 });
  };

  return (
    <div className="panel search-panel">
      <div className="search-grid">
        <label className="search-span-2">
          통합 검색
          <input
            value={filters.q}
            placeholder="파일명, 경로, 메타데이터 키/값 검색"
            onChange={(event) => onChange({ q: event.target.value, page: 1 })}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                onSubmit();
              }
            }}
          />
        </label>
        <div className="metadata-filter-editor search-span-2">
          <div className="metadata-filter-header">
            <strong>메타데이터 필터</strong>
            <button type="button" className="secondary" onClick={addMetadataFilter}>
              조건 추가
            </button>
          </div>
          {metadataFilters.map((metadataFilter, index) => (
            <div className="metadata-filter-row" key={`metadata-filter-${index}`}>
              <label>
                Key
                <input
                  list="metadata-keys"
                  value={metadataFilter.key}
                  placeholder="예: View"
                  onChange={(event) => updateMetadataFilter(index, { key: event.target.value })}
                />
              </label>
              <label>
                Value
                <input
                  value={metadataFilter.value}
                  placeholder="비워두면 key 존재 여부만 필터"
                  onChange={(event) => updateMetadataFilter(index, { value: event.target.value })}
                />
              </label>
              <button
                type="button"
                className="secondary"
                disabled={metadataFilters.length <= 1}
                onClick={() => removeMetadataFilter(index)}
              >
                제거
              </button>
            </div>
          ))}
          <datalist id="metadata-keys">
            {metadataKeys.map((key) => (
              <option key={key} value={key} />
            ))}
          </datalist>
        </div>
        <label>
          너비 최소
          <input value={filters.widthMin} onChange={(event) => onChange({ widthMin: event.target.value, page: 1 })} />
        </label>
        <label>
          너비 최대
          <input value={filters.widthMax} onChange={(event) => onChange({ widthMax: event.target.value, page: 1 })} />
        </label>
        <label>
          높이 최소
          <input value={filters.heightMin} onChange={(event) => onChange({ heightMin: event.target.value, page: 1 })} />
        </label>
        <label>
          높이 최대
          <input value={filters.heightMax} onChange={(event) => onChange({ heightMax: event.target.value, page: 1 })} />
        </label>
        <label>
          파일 크기 최소(byte)
          <input value={filters.sizeMin} onChange={(event) => onChange({ sizeMin: event.target.value, page: 1 })} />
        </label>
        <label>
          파일 크기 최대(byte)
          <input value={filters.sizeMax} onChange={(event) => onChange({ sizeMax: event.target.value, page: 1 })} />
        </label>
        <label>
          수정 시작
          <input
            type="datetime-local"
            value={filters.modifiedFrom}
            onChange={(event) => onChange({ modifiedFrom: event.target.value, page: 1 })}
          />
        </label>
        <label>
          수정 종료
          <input
            type="datetime-local"
            value={filters.modifiedTo}
            onChange={(event) => onChange({ modifiedTo: event.target.value, page: 1 })}
          />
        </label>
        <label>
          알파 채널
          <select
            value={filters.hasAlpha}
            onChange={(event) => onChange({ hasAlpha: event.target.value as SearchFilters["hasAlpha"], page: 1 })}
          >
            <option value="">전체</option>
            <option value="true">있음</option>
            <option value="false">없음</option>
          </select>
        </label>
        <label>
          상태
          <select value={filters.status} onChange={(event) => onChange({ status: event.target.value, page: 1 })}>
            <option value="">전체</option>
            {Object.entries(STATUS_LABELS)
              .filter(([value]) => value !== "missing")
              .map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
          </select>
        </label>
        <label>
          정렬
          <select value={filters.sort} onChange={(event) => onChange({ sort: event.target.value as SearchFilters["sort"] })}>
            <option value="modified_time">수정 시각</option>
            <option value="filename">파일명</option>
            <option value="path">경로</option>
            <option value="file_size">파일 크기</option>
            <option value="width">너비</option>
            <option value="height">높이</option>
          </select>
        </label>
        <label>
          순서
          <select value={filters.order} onChange={(event) => onChange({ order: event.target.value as SearchFilters["order"] })}>
            <option value="desc">내림차순</option>
            <option value="asc">오름차순</option>
          </select>
        </label>
      </div>
      <div className="search-actions">
        <button onClick={onSubmit}>검색 적용</button>
        <button className="secondary" onClick={onReset}>
          필터 초기화
        </button>
      </div>
    </div>
  );
}
