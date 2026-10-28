import type { useScenarioFocus } from "../../../hooks/useScenarioFocus";
import type { ScenarioDetailResponse } from "../../../types/scenario";

export interface ScenarioContentColumnProps {
  scenario: ScenarioDetailResponse;
  focus: ReturnType<typeof useScenarioFocus>;
}
