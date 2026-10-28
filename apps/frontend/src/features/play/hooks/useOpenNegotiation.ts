import { useMutation, useQueryClient } from "@tanstack/react-query";
import { openNegotiation } from "../api/scene.api";
import { OPEN_NEGOTIATION_FALLBACK_MESSAGE } from "../constants/scene.constants";
import { buildOperationGuard } from "../lib/operationGuard";
import { parseSimulationError } from "../lib/simulationError";
import { useStrategyPlayStore } from "../stores/strategyPlay.store";
import type { MutationResponse } from "../types/simulation.types";
import { getWorldQueryKey, readCachedWorld } from "./useSimulationCommands";

const MISSING_PLAYTHROUGH_MESSAGE = "Playthrough ID is required";

export function useOpenNegotiation(playthroughId?: string) {
  const queryClient = useQueryClient();

  const invalidateWorld = (): void => {
    void queryClient.invalidateQueries({ queryKey: getWorldQueryKey(playthroughId) });
  };

  const mutation = useMutation<MutationResponse, Error, string>({
    mutationFn: (counterpartFactionId) => {
      if (!playthroughId) throw new Error(MISSING_PLAYTHROUGH_MESSAGE);
      const guard = buildOperationGuard(readCachedWorld(queryClient, playthroughId));
      return openNegotiation(playthroughId, guard, counterpartFactionId);
    },
    onSuccess: (response) => {
      if (response.scene_id) useStrategyPlayStore.getState().openScene(response.scene_id);
      invalidateWorld();
    },
    onError: invalidateWorld,
  });

  const errorMessage = mutation.error
    ? parseSimulationError(mutation.error, OPEN_NEGOTIATION_FALLBACK_MESSAGE).message
    : null;

  return {
    openNegotiation: mutation.mutate,
    isOpening: mutation.isPending,
    errorMessage,
  };
}
