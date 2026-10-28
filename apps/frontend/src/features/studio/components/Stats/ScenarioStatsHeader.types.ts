import type { StatsRange, StatsScenarioSummary } from "../../types/stats.types";

export interface ScenarioStatsHeaderProps {
  scenarioId: string;
  scenario: StatsScenarioSummary | undefined;
  range: StatsRange;
  onRangeChange: (range: StatsRange) => void;
}
