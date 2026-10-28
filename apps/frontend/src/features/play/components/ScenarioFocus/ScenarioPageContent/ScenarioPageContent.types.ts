import type { useScenarioFocus } from "../../../hooks/useScenarioFocus";
import type { ScenarioDetailResponse } from "../../../types/scenario";

export interface ScenarioPageContentProps {
  scenario: ScenarioDetailResponse;
  focus: ReturnType<typeof useScenarioFocus>;
}
