import { useQuery } from "@tanstack/react-query";
import { getScenario } from "../api/scenarios.api";
import {
  SCENARIO_QUERY_KEY,
  STUDIO_SCENARIO_STALE_TIME_MS,
} from "../constants/studioScenario";
import type { ScenarioResponse } from "../types/scenario.types";

export const useStudioScenario = (scenarioId: string | null) => {
  const scenarioQuery = useQuery<ScenarioResponse, Error>({
    queryKey: [SCENARIO_QUERY_KEY, scenarioId],
    queryFn: () => getScenario(scenarioId as string),
    enabled: Boolean(scenarioId),
    staleTime: STUDIO_SCENARIO_STALE_TIME_MS,
    refetchOnWindowFocus: false,
  });

  return {
    scenario: scenarioQuery.data ?? null,
    isLoading: scenarioQuery.isLoading,
    error: scenarioQuery.error,
  };
};
