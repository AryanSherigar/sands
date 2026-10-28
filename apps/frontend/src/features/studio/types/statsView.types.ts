export type ChartTone = "neutral" | "accent";

export interface ChartDatum {
  label: string;
  value: number;
}

export interface BarListItem {
  label: string;
  fraction: number;
  valueLabel: string;
}

export interface StatsTableData {
  columns: string[];
  rows: string[][];
}

export interface StatsSectionLink {
  id: string;
  label: string;
}

export type ScenarioSortKey =
  | "title"
  | "plays"
  | "trend"
  | "completion_rate"
  | "average_turns"
  | "average_rating";

export type SortDirection = "ascending" | "descending";

export interface ScenarioTableColumn {
  key: ScenarioSortKey;
  label: string;
}

export type CopyState = "idle" | "copied" | "failed";
