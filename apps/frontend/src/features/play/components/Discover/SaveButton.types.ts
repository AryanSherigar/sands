import type { ScenarioSummaryResponse } from "@/shared/types/scenarioSummary.types";

export interface SaveButtonProps {
  scenario: ScenarioSummaryResponse;
  onToggleSave: (scenario: ScenarioSummaryResponse) => void;
}
