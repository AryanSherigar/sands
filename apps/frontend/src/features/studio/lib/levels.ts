import type { MeterTier } from "@/shared/types/display-hints.types";

export interface LevelRow {
  id: string;
  name: string;
  min: number | undefined;
}

const DUPLICATE_THRESHOLD_PROBLEM = "Each level needs its own threshold.";
const MULTIPLE_OPEN_LEVELS_PROBLEM = "Only one level can have no threshold: the last one.";

export const toLevelRows = (tiers: readonly MeterTier[], prefix = "level"): LevelRow[] =>
  tiers.map((tier, index) => ({ id: `${prefix}-${index}`, name: tier.name, min: tier.min }));

const withThresholds = (rows: readonly LevelRow[]): number[] =>
  rows.flatMap((row) => (row.min === undefined ? [] : [row.min]));

export const findLevelProblem = (rows: readonly LevelRow[]): string | null => {
  if (rows.filter((row) => row.min === undefined).length > 1) return MULTIPLE_OPEN_LEVELS_PROBLEM;
  const thresholds = withThresholds(rows);
  return new Set(thresholds).size === thresholds.length ? null : DUPLICATE_THRESHOLD_PROBLEM;
};

const byThresholdDescending = (first: LevelRow, second: LevelRow): number => {
  if (first.min === undefined) return 1;
  if (second.min === undefined) return -1;
  return second.min - first.min;
};

export const sortLevelRows = (rows: readonly LevelRow[]): LevelRow[] => [...rows].sort(byThresholdDescending);

export const toValidTiers = (rows: readonly LevelRow[]): MeterTier[] | null => {
  if (findLevelProblem(rows) !== null) return null;
  return sortLevelRows(rows).map((row) => (row.min === undefined ? { name: row.name } : { name: row.name, min: row.min }));
};

export const nextLevelThreshold = (rows: readonly LevelRow[]): number => {
  const thresholds = withThresholds(rows);
  return thresholds.length === 0 ? 0 : Math.min(...thresholds) - 1;
};
