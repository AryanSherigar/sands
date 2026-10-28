import type { OverviewScenarioRow } from "../types/stats.types";
import type { ScenarioSortKey, SortDirection } from "../types/statsView.types";

type SortValue = string | number | null;

const sortValue = (row: OverviewScenarioRow, key: ScenarioSortKey): SortValue => {
  if (key === "title") return row.title.toLowerCase();
  if (key === "trend") return row.trend?.percent_change ?? null;
  return row[key];
};

const compareDefined = (left: string | number, right: string | number): number => {
  if (typeof left === "string" && typeof right === "string") {
    return left.localeCompare(right);
  }
  return Number(left) - Number(right);
};

const compareValues = (
  left: SortValue,
  right: SortValue,
  direction: SortDirection,
): number => {
  if (left === right) return 0;
  if (left === null) return 1;
  if (right === null) return -1;
  const order = compareDefined(left, right);
  return direction === "ascending" ? order : -order;
};

export const sortScenarioRows = (
  rows: OverviewScenarioRow[],
  key: ScenarioSortKey,
  direction: SortDirection,
): OverviewScenarioRow[] =>
  [...rows].sort((left, right) =>
    compareValues(sortValue(left, key), sortValue(right, key), direction),
  );

export const toggleSortDirection = (direction: SortDirection): SortDirection =>
  direction === "ascending" ? "descending" : "ascending";
