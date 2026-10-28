import React from "react";
import { ActiveFilterChips } from "./ActiveFilterChips";
import { SortSelect } from "./SortSelect";
import { ViewToggle } from "./ViewToggle";
import type { ResultsHeaderProps } from "./ResultsHeader.types";

const SUBTITLE =
  "Explore community authored and curated narrative worlds powered by autonomous agents.";

const formatCount = (query: string, totalCount: number): string =>
  query ? `Results for '${query}' · ${totalCount}` : `${totalCount} stories`;

export const ResultsHeader: React.FC<ResultsHeaderProps> = ({
  query,
  totalCount,
  chips,
  sort,
  view,
  onRemoveChip,
  onClearAll,
  onSortChange,
  onViewChange,
}) => (
  <div className="flex flex-col gap-4">
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-2xl font-bold tracking-tight text-content lg:text-3xl">
            Discover scenarios
          </h1>
          <span
            aria-live="polite"
            className="rounded-full border border-border-subtle bg-surface-raised px-2.5 py-0.5 font-mono text-xs text-content-muted"
          >
            {formatCount(query, totalCount)}
          </span>
        </div>
        <p className="mt-0.5 text-[0.8125rem] text-content-faint">{SUBTITLE}</p>
      </div>
      <div className="flex shrink-0 items-center gap-2.5 self-start sm:self-auto">
        <SortSelect value={sort} onChange={onSortChange} />
        <ViewToggle value={view} onChange={onViewChange} />
      </div>
    </div>
    <ActiveFilterChips chips={chips} onRemove={onRemoveChip} onClearAll={onClearAll} />
  </div>
);
