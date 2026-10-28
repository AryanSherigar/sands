import type React from "react";
import type { ScenarioSummaryResponse } from "@/shared/types/scenarioSummary.types";
import type { UseScenarioListResult } from "../../hooks/useScenarioList";
import type { DiscoverView } from "../../types/discover.types";

export interface DiscoverResultsProps {
  list: UseScenarioListResult;
  view: DiscoverView;
  emptyState: React.ReactNode;
  onToggleSave: (scenario: ScenarioSummaryResponse) => void;
}
