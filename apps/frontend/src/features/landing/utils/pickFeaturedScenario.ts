import type { ScenarioSummaryResponse } from "@/shared/types/scenarioSummary.types";

const FLAGSHIP_TITLE = "The Last Archivist of Oakhaven";

const computeScore = (scenario: ScenarioSummaryResponse): number => {
  if (scenario.title === FLAGSHIP_TITLE) return 1000;
  const rating = Number.parseFloat(scenario.rating_avg) || 0;
  return rating * Math.log10(scenario.play_count + 10);
};

export const pickFeaturedScenario = (
  scenarios: ScenarioSummaryResponse[],
): ScenarioSummaryResponse | null => {
  const withCover = scenarios.filter((scenario) => scenario.cover_image_url);
  const candidates = withCover.length > 0 ? withCover : scenarios;
  return [...candidates].sort((a, b) => computeScore(b) - computeScore(a))[0] ?? null;
};
