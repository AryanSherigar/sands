import type { StatsRange, Trend } from "../../types/stats.types";

export interface TrendLabelProps {
  trend: Trend | null;
  range: StatsRange;
}
