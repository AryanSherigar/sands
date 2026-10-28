import type { ScenarioSummaryResponse } from "@/shared/types/scenarioSummary.types";

export const FALLBACK_COVER_URL = "/images/hero.png";
const RATING_FRACTION_DIGITS = 1;

export const getPrimaryGenre = (scenario: ScenarioSummaryResponse): string | null =>
  scenario.genre_tags[0] ?? null;

export const getTypeLabel = (scenario: ScenarioSummaryResponse): string =>
  scenario.mode === "master" ? "Advanced" : "Simple";

export const formatRating = (scenario: ScenarioSummaryResponse): string =>
  Number.parseFloat(scenario.rating_avg || "0").toFixed(RATING_FRACTION_DIGITS);

export const formatPlayCount = (scenario: ScenarioSummaryResponse): string =>
  `${scenario.play_count.toLocaleString()} plays`;
