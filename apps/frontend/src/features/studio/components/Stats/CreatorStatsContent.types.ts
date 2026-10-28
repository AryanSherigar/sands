import type { CreatorStatsOverviewResponse } from "../../types/stats.types";

export interface CreatorStatsContentProps {
  overview: CreatorStatsOverviewResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}
