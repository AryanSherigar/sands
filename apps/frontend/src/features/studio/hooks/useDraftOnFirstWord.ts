import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import { createScenario } from "../api/scenarios.api";
import { MY_SCENARIOS_QUERY_KEY } from "../constants/studio-list";
import { SCENARIO_QUERY_KEY } from "../constants/studioScenario";
import { enableEditGuard } from "../lib/editGuard";
import { buildDraftPayload } from "../lib/scenarioPatch";
import type { ScenarioResponse } from "../types/scenario.types";
import type { ScenarioFieldsPatch } from "../types/scenarioPatch.types";

interface UseDraftOnFirstWordOptions {
  onCreated: (scenario: ScenarioResponse) => void;
}

export const useDraftOnFirstWord = ({ onCreated }: UseDraftOnFirstWordOptions) => {
  const queryClient = useQueryClient();
  const draftRef = useRef<Promise<ScenarioResponse> | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const createDraft = useCallback(
    (seed: ScenarioFieldsPatch): Promise<ScenarioResponse> => {
      if (draftRef.current) return draftRef.current;
      setIsCreating(true);
      const request = createScenario(buildDraftPayload(seed))
        .then((created) => {
          enableEditGuard(created.scenario_id);
          queryClient.setQueryData([SCENARIO_QUERY_KEY, created.scenario_id], created);
          queryClient.invalidateQueries({ queryKey: [MY_SCENARIOS_QUERY_KEY] });
          onCreated(created);
          return created;
        })
        .catch((error: unknown) => {
          draftRef.current = null;
          throw error;
        })
        .finally(() => setIsCreating(false));
      draftRef.current = request;
      return request;
    },
    [onCreated, queryClient],
  );

  return { createDraft, isCreating };
};
