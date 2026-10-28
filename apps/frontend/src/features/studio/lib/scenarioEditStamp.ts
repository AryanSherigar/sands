import type { QueryClient } from "@tanstack/react-query";
import type { ScenarioResponse } from "../types/scenario.types";

export const applyScenarioEditStamp = (
  queryClient: QueryClient,
  scenarioId: string | null,
  stamp: string | null | undefined,
): void => {
  if (!stamp) return;
  queryClient.setQueryData<ScenarioResponse>(["scenario", scenarioId], (old) =>
    old ? { ...old, content_edited_at: stamp } : old,
  );
};
