import React from "react";
import { STATS_RANGE_LABELS, STATS_RANGES } from "../../constants/stats";
import type { StatsRange } from "../../types/stats.types";
import type { RangePickerProps } from "./RangePicker.types";

const OPTION_BASE =
  "rounded-sm px-3 py-1 font-mono text-xs tabular-nums transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent";
const OPTION_SELECTED = "bg-surface-overlay text-content";
const OPTION_IDLE = "text-content-muted hover:text-content";

export const RangePicker: React.FC<RangePickerProps> = ({ value, onChange }) => {
  const handleSelect = (range: StatsRange) => (): void => onChange(range);
  return (
    <div
      role="radiogroup"
      aria-label="Time range"
      className="inline-flex rounded-md border border-border-subtle bg-surface-raised p-0.5"
    >
      {STATS_RANGES.map((range) => {
        const isSelected = range === value;
        return (
          <button
            key={range}
            type="button"
            role="radio"
            aria-checked={isSelected}
            onClick={handleSelect(range)}
            className={`${OPTION_BASE} ${isSelected ? OPTION_SELECTED : OPTION_IDLE}`}
          >
            {STATS_RANGE_LABELS[range]}
          </button>
        );
      })}
    </div>
  );
};
