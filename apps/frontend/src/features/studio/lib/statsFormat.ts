import {
  BENCHMARK_RATE_KEYS,
  EMPTY_STAT_VALUE,
  PERCENT_SCALE,
  PREVIOUS_RANGE_COPY,
  RANGE_PERIOD_COPY,
} from "../constants/stats";
import type {
  BenchmarkKey,
  StatsBucket,
  StatsRange,
  Trend,
} from "../types/stats.types";

const NUMBER_LOCALE = "en-US";

export const formatCount = (value: number | null): string => {
  if (value === null) return EMPTY_STAT_VALUE;
  return Math.round(value).toLocaleString(NUMBER_LOCALE);
};

export const formatPercent = (rate: number | null): string => {
  if (rate === null) return EMPTY_STAT_VALUE;
  return `${Math.round(rate * PERCENT_SCALE)}%`;
};

export const formatDecimal = (value: number | null): string => {
  if (value === null) return EMPTY_STAT_VALUE;
  return value.toFixed(1);
};

export const formatTrend = (trend: Trend | null, range: StatsRange): string | null => {
  if (trend === null) return null;
  if (trend.is_new) return "New";
  if (trend.percent_change === null) return null;
  const percent = Math.round(Math.abs(trend.percent_change) * PERCENT_SCALE);
  const arrow = trend.percent_change < 0 ? "↓" : "↑";
  return `${arrow} ${percent}% vs ${PREVIOUS_RANGE_COPY[range]}`;
};

export const trendToneClass = (trend: Trend): string => {
  const change = trend.percent_change;
  if (trend.is_new || change === null || change === 0) return "text-content-muted";
  if (change > 0) return "text-success";
  return "text-danger";
};

export const summarizePlays = (
  totalPlays: number,
  trend: Trend | null,
  range: StatsRange,
): string => {
  const base = `${formatCount(totalPlays)} plays in ${RANGE_PERIOD_COPY[range]}`;
  const trendText = formatTrend(trend, range);
  if (trendText === null) return `${base}.`;
  return `${base} (${trendText}).`;
};

export const formatBucketLabel = (bucketStart: string, bucket: StatsBucket): string => {
  const label = new Date(`${bucketStart}T00:00:00Z`).toLocaleDateString(NUMBER_LOCALE, {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
  if (bucket === "week") return `Week of ${label}`;
  return label;
};

export const formatBenchmarkValue = (key: BenchmarkKey, value: number | null): string => {
  if (BENCHMARK_RATE_KEYS.includes(key)) return formatPercent(value);
  return formatDecimal(value);
};
