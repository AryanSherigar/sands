import type { ScenarioSummaryResponse } from "@/shared/types/scenarioSummary.types";

export interface ScenarioRowCardProps {
  scenario: ScenarioSummaryResponse;
  onToggleSave: (scenario: ScenarioSummaryResponse) => void;
}
