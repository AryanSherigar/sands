import React from "react";
import type { TurnReportCategory } from "../../../types/turnReport.types";
import type {
  ReportCategoryCounts,
  ReportFilterPillsProps,
} from "./ReportFilterPills.types";

interface FilterOption {
  id: TurnReportCategory;
  label: string;
}

const FILTERS: FilterOption[] = [
  { id: "all", label: "All" },
  { id: "military", label: "Military" },
  { id: "economy", label: "Economy" },
  { id: "diplomacy", label: "Diplomacy" },
  { id: "internal", label: "Internal" },
];

const getPillClass = (isActive: boolean): string =>
  isActive
    ? "bg-[#3A3128] text-[#F7F0DC] font-semibold shadow-sm"
    : "bg-[#F3EAD3] text-[#55493E] hover:bg-[#EBE0C5] border border-[#3A3128]/15";

const renderPill = (
  filter: FilterOption,
  activeFilter: TurnReportCategory,
  counts: ReportCategoryCounts,
  onSelect: (filter: TurnReportCategory) => void,
): React.ReactNode => {
  const isSelected = activeFilter === filter.id;
  const count = counts[filter.id];

  return (
    <button
      key={filter.id}
      type="button"
      onClick={() => onSelect(filter.id)}
      className={`px-2.5 py-1 text-xs rounded-full transition-colors flex items-center gap-1 ${getPillClass(isSelected)}`}
    >
      <span>{filter.label}</span>
      {count > 0 ? (
        <span className="text-[10px] opacity-75">({count})</span>
      ) : null}
    </button>
  );
};

export const ReportFilterPills: React.FC<ReportFilterPillsProps> = ({
  activeFilter,
  counts,
  onSelectFilter,
}) => (
  <nav
    aria-label="Report Categories"
    className="flex items-center gap-1.5 px-4 py-2 border-b border-[#3A3128]/10 overflow-x-auto"
  >
    {FILTERS.map((filter) =>
      renderPill(filter, activeFilter, counts, onSelectFilter),
    )}
  </nav>
);
