import type { TurnReportCategory } from "../../../types/turnReport.types";

export interface ReportCategoryCounts {
  all: number;
  military: number;
  economy: number;
  diplomacy: number;
  internal: number;
}

export interface ReportFilterPillsProps {
  activeFilter: TurnReportCategory;
  counts: ReportCategoryCounts;
  onSelectFilter: (filter: TurnReportCategory) => void;
}
