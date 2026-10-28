import type { OverviewScenarioRow, StatsRange } from "../../types/stats.types";

export interface ScenarioStatsTableProps {
  rows: OverviewScenarioRow[];
  range: StatsRange;
}
