import { DEFAULT_STATS_RANGE, STATS_RANGES } from "../constants/stats";
import type { StatsRange } from "../types/stats.types";

const isStatsRange = (value: string | null): value is StatsRange =>
  value !== null && (STATS_RANGES as readonly string[]).includes(value);

export const parseStatsRange = (value: string | null): StatsRange =>
  isStatsRange(value) ? value : DEFAULT_STATS_RANGE;
