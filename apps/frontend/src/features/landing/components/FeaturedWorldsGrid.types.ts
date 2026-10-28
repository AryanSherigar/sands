import type { ScenarioSummaryResponse } from "@/shared/types/scenarioSummary.types";

export interface FeaturedWorldsGridProps {
  scenarios: ScenarioSummaryResponse[];
  totalCount?: number;
}
