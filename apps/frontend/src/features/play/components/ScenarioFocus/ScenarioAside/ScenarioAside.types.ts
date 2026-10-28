import type { useScenarioFocus } from "../../../hooks/useScenarioFocus";
import type { ScenarioDetailResponse } from "../../../types/scenario";
import type { InProgressSummary } from "../../../types/scenarioPage.types";

export interface ScenarioAsideProps {
  scenario: ScenarioDetailResponse;
  focus: ReturnType<typeof useScenarioFocus>;
  inProgress: InProgressSummary;
  isPlayCardVisible: boolean;
  isDraft: boolean;
  isStartingPlaytest: boolean;
  onPlaytest: () => void;
}
