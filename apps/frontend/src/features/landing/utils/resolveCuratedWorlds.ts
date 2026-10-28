import type { ScenarioSummaryResponse } from "@/shared/types/scenarioSummary.types";

const MAX_CURATED_WORLDS = 4;

export const resolveCuratedWorlds = (
  items: ScenarioSummaryResponse[] = [],
  excludeScenarioId?: string,
): ScenarioSummaryResponse[] =>
  items
    .filter(
      (item) =>
        item.scenario_id !== excludeScenarioId &&
        item.title !== "The Last Archivist of Oakhaven",
    )
    .slice(0, MAX_CURATED_WORLDS);
