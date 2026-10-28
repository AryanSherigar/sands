import type { StatsRange } from "../../types/stats.types";

export interface RangePickerProps {
  value: StatsRange;
  onChange: (range: StatsRange) => void;
}
