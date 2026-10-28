import { useQuery } from "@tanstack/react-query";
import { getSceneView } from "../api/scene.api";
import { getSceneQueryKey } from "../constants/scene.constants";
import type { SceneViewResponse } from "../types/scene.types";

export function useSceneView(playthroughId?: string, sceneId?: string | null) {
  return useQuery<SceneViewResponse, Error>({
    queryKey: getSceneQueryKey(playthroughId, sceneId),
    queryFn: () => {
      if (!playthroughId || !sceneId) throw new Error("Scene identity is required");
      return getSceneView(playthroughId, sceneId);
    },
    enabled: Boolean(playthroughId && sceneId),
    staleTime: 0,
  });
}
