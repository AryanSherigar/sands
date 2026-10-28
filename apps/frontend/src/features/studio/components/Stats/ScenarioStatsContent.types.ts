import type { ScenarioStatsResponse } from "../../types/stats.types";

export interface ScenarioStatsContentProps {
  stats: ScenarioStatsResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  errorStatus: number | null;
  onRetry: () => void;
}
