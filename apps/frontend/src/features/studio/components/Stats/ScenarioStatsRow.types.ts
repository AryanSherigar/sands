import type { OverviewScenarioRow, StatsRange } from "../../types/stats.types";

export interface ScenarioStatsRowProps {
  row: OverviewScenarioRow;
  range: StatsRange;
  onSelect: () => void;
}
