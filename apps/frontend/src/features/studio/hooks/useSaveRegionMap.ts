import { useMutation, useQueryClient } from "@tanstack/react-query";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import type { MapDocument } from "@/shared/types/strategy-map.types";
import { saveRegionMap } from "../api/regionMap.api";
import { SAVE_ERROR_FALLBACK } from "../constants/regionMap";
import { SCENARIO_QUERY_KEY } from "../constants/studioScenario";
import { STRATEGY_MAP_QUERY_KEY } from "./useStrategyMap";

export const useSaveRegionMap = (scenarioId: string) => {
  const queryClient = useQueryClient();
  const mutation = useMutation<MapDocument, Error, MapDocument>({
    mutationFn: (document) => saveRegionMap(scenarioId, document),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [SCENARIO_QUERY_KEY, scenarioId] });
      void queryClient.invalidateQueries({ queryKey: [STRATEGY_MAP_QUERY_KEY, scenarioId] });
    },
  });
  return {
    mutateAsync: mutation.mutateAsync,
    isSaving: mutation.isPending,
    errorMessage: mutation.error
      ? extractErrorMessage(mutation.error, SAVE_ERROR_FALLBACK)
      : null,
  };
};
