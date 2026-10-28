import { useMutation, useQueryClient } from "@tanstack/react-query";
import { decideScene } from "../api/scene.api";
import {
  SCENE_DECISION_FALLBACK_MESSAGE,
  TERMS_CHANGED_CODE,
  TERMS_CHANGED_MESSAGE,
  getSceneQueryKey,
} from "../constants/scene.constants";
import { buildOperationGuard } from "../lib/operationGuard";
import { parseSimulationError } from "../lib/simulationError";
import type { SceneDecisionInput } from "../types/scene.types";
import type { MutationResponse } from "../types/simulation.types";
import { getWorldQueryKey, readCachedWorld } from "./useSimulationCommands";

const MISSING_SCENE_MESSAGE = "Scene identity is required";

function describeDecisionError(error: Error): string {
  const info = parseSimulationError(error, SCENE_DECISION_FALLBACK_MESSAGE);
  return info.code === TERMS_CHANGED_CODE ? TERMS_CHANGED_MESSAGE : info.message;
}

export function useSceneDecision(playthroughId?: string, sceneId?: string | null) {
  const queryClient = useQueryClient();

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: getWorldQueryKey(playthroughId) });
    void queryClient.invalidateQueries({
      queryKey: getSceneQueryKey(playthroughId, sceneId),
    });
  };

  const mutation = useMutation<MutationResponse, Error, SceneDecisionInput>({
    mutationFn: (input) => {
      if (!playthroughId || !sceneId) throw new Error(MISSING_SCENE_MESSAGE);
      const guard = buildOperationGuard(readCachedWorld(queryClient, playthroughId));
      return decideScene(playthroughId, sceneId, guard, input);
    },
    onSettled: refresh,
  });

  return {
    decide: mutation.mutate,
    isDeciding: mutation.isPending,
    errorMessage: mutation.error ? describeDecisionError(mutation.error) : null,
  };
}
