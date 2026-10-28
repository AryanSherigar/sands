import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  FINAL_SCENE_STATUSES,
  getSceneQueryKey,
} from "../constants/scene.constants";
import { useSceneDecision } from "./useSceneDecision";
import { useSceneStream } from "./useSceneStream";
import { useSceneView } from "./useSceneView";
import { getWorldQueryKey } from "./useSimulationCommands";

export function useSceneDialog(playthroughId: string, sceneId: string) {
  const queryClient = useQueryClient();
  const { data: scene } = useSceneView(playthroughId, sceneId);
  const decision = useSceneDecision(playthroughId, sceneId);

  const refreshAfterExchange = useCallback(
    () =>
      Promise.all([
        queryClient.invalidateQueries({
          queryKey: getSceneQueryKey(playthroughId, sceneId),
        }),
        queryClient.invalidateQueries({ queryKey: getWorldQueryKey(playthroughId) }),
      ]),
    [queryClient, playthroughId, sceneId],
  );
  const stream = useSceneStream(sceneId, refreshAfterExchange);

  const isFinished = scene ? FINAL_SCENE_STATUSES.includes(scene.status) : false;
  const isBusy = stream.isStreaming || decision.isDeciding;

  return { scene, isFinished, isBusy, stream, decision };
}
