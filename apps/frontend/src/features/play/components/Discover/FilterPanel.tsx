import React from "react";
import { TYPE_OPTIONS } from "../../constants/discover.constants";
import { GenreFilter } from "./GenreFilter";
import { LibraryFilter } from "./LibraryFilter";
import { MatureSwitch } from "./MatureSwitch";
import { SegmentedControl } from "./SegmentedControl";
import type { FilterPanelProps } from "./FilterPanel.types";

const SECTION_CLASSES =
  "border-b border-border-subtle pb-5 pt-5 first:pt-0";

export const FilterPanel: React.FC<FilterPanelProps> = ({
  filters,
  hasActiveFilters,
  isAuthenticated,
  onChange,
  onClearAll,
  onSignIn,
}) => (
  <div className="flex flex-col gap-5">
    <div className="flex flex-col">
      <div className={SECTION_CLASSES}>
        <LibraryFilter
          value={filters.library}
          isAuthenticated={isAuthenticated}
          onChange={(library) => onChange({ ...filters, library })}
          onSignIn={onSignIn}
        />
      </div>
      <div className={SECTION_CLASSES}>
        <GenreFilter
          selected={filters.genres}
          onChange={(genres) => onChange({ ...filters, genres })}
        />
      </div>
      <div className={SECTION_CLASSES}>
        <SegmentedControl
          legend="Type / Mode"
          options={TYPE_OPTIONS}
          value={filters.type}
          onChange={(type) => onChange({ ...filters, type })}
        />
      </div>
      <div className="pt-5">
        <MatureSwitch
          isChecked={filters.isMatureIncluded}
          onChange={() =>
            onChange({ ...filters, isMatureIncluded: !filters.isMatureIncluded })
          }
        />
      </div>
    </div>
    {hasActiveFilters && (
      <button
        type="button"
        onClick={onClearAll}
        className="ml-3 w-fit text-sm text-content-faint underline decoration-border-strong underline-offset-4 hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
      >
        Clear all
      </button>
    )}
  </div>
);
