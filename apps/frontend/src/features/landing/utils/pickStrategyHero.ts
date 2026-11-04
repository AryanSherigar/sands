import type { ScenarioSummaryResponse } from "@/shared/types/scenarioSummary.types";

export const pickStrategyHero = (
  strategyScenarios: ScenarioSummaryResponse[] = [],
): ScenarioSummaryResponse | null =>
  strategyScenarios.find((scenario) => scenario.cover_image_url) ??
  strategyScenarios[0] ??
  null;
