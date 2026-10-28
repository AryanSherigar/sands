import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { fetchUserPlaythroughs } from "@/shared/api/playthroughs.api";
import type { UserPlaythroughSummary } from "@/shared/types/playthroughSummary.types";
import type { InProgressSummary } from "../types/scenarioPage.types";
import { summarizeInProgress } from "../utils/scenarioPage.utils";

const ACTIVE_STATUS = "active";

export const useScenarioRuns = (scenarioId: string | undefined) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const runsQuery = useQuery<UserPlaythroughSummary[], Error>({
    queryKey: ["user-playthroughs", ACTIVE_STATUS],
    queryFn: () => fetchUserPlaythroughs(ACTIVE_STATUS),
    enabled: isAuthenticated && Boolean(scenarioId),
    staleTime: 0,
  });

  const inProgress: InProgressSummary = scenarioId
    ? summarizeInProgress(runsQuery.data ?? [], scenarioId)
    : { kind: "none" };

  return {
    inProgress,
    isError: runsQuery.isError,
    refetch: runsQuery.refetch,
  };
};
