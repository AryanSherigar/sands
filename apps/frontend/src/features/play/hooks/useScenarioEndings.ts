import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { fetchScenarioEndings } from "../api/scenarioFocus.api";
import type { ScenarioEndingsResponse } from "../types/scenario";

export const useScenarioEndings = (scenarioId: string | undefined) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const endingsQuery = useQuery<ScenarioEndingsResponse, Error>({
    // NOTE: keyed on auth state because the API returns the viewer's own found
    // endings only when signed in; a cached signed-out answer must not be reused.
    queryKey: ["scenario-endings", scenarioId, isAuthenticated],
    queryFn: () => {
      if (!scenarioId) throw new Error("Scenario ID is required");
      return fetchScenarioEndings(scenarioId);
    },
    enabled: Boolean(scenarioId),
    staleTime: 0,
  });

  return {
    endings: endingsQuery.data,
    isEndingsError: endingsQuery.isError,
    refetchEndings: () => void endingsQuery.refetch(),
  };
};
