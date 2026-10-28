import type { SeriesPoint, StatsBucket } from "../types/stats.types";
import type { ChartDatum, StatsTableData } from "../types/statsView.types";
import { formatBucketLabel, formatCount } from "./statsFormat";

export const toSeriesData = (series: SeriesPoint[], bucket: StatsBucket): ChartDatum[] =>
  series.map((point) => ({
    label: formatBucketLabel(point.bucket_start, bucket),
    value: point.plays,
  }));

export const toChartTable = (
  data: ChartDatum[],
  labelHeader: string,
  valueHeader: string,
): StatsTableData => ({
  columns: [labelHeader, valueHeader],
  rows: data.map((datum) => [datum.label, formatCount(datum.value)]),
});

export const describeLargestBucket = (data: ChartDatum[], unit: string): string => {
  const largest = data.reduce<ChartDatum | null>(
    (best, datum) => (best === null || datum.value > best.value ? datum : best),
    null,
  );
  if (largest === null || largest.value === 0) return `No ${unit} yet.`;
  return `Most common: ${largest.label} (${formatCount(largest.value)} ${unit}).`;
};
