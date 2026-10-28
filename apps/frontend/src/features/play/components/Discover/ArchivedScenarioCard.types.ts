import type { ScenarioSummaryResponse } from "@/shared/types/scenarioSummary.types";

export type ArchivedScenarioCardLayout = "row" | "poster";

export interface ArchivedScenarioCardProps {
  scenario: ScenarioSummaryResponse;
  layout: ArchivedScenarioCardLayout;
}
