import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";
import { SCENARIO_QUERY_KEY } from "../constants/studioScenario";
import { buildStateField, buildValueKey } from "../lib/trackedValueSchema";
import { usesStatusHud } from "../lib/trackedValueEditing";
import { listTrackedValueOptions } from "../lib/valueOptions";
import type { StateFieldDefinition, ScenarioResponse } from "../types/scenario.types";
import type { ValueOption } from "../types/sentence.types";
import type { NewTrackedValue } from "../types/trackedValue.types";
import { useEnsureTool } from "./useEnsureTool";
import { useGuide } from "./useGuide";

export interface TrackedValues {
  values: ValueOption[];
  addValue: (input: NewTrackedValue) => Promise<ValueOption>;
}

const readCachedSchema = (
  scenario: ScenarioResponse | undefined,
): Record<string, StateFieldDefinition> => scenario?.state_schema ?? {};

export const useTrackedValues = (): TrackedValues => {
  const { scenario, ensureDraft, saveFields, flushSaves } = useGuide();
  const { ensureTool } = useEnsureTool();
  const queryClient = useQueryClient();
  const stateSchema = scenario?.state_schema;
  const values = useMemo(() => listTrackedValueOptions(stateSchema ?? {}), [stateSchema]);

  const addValue = useCallback(
    async (input: NewTrackedValue): Promise<ValueOption> => {
      const scenarioId = await ensureDraft();
      await flushSaves();
      const cached = queryClient.getQueryData<ScenarioResponse>([SCENARIO_QUERY_KEY, scenarioId]);
      const schema = readCachedSchema(cached);
      const key = buildValueKey(input.name, new Set(Object.keys(schema)));
      const field = buildStateField(input);
      if (usesStatusHud(field)) await ensureTool("status_hud");
      const next = { ...schema, [key]: field };
      saveFields({ state_schema: next });
      await flushSaves();
      const created = listTrackedValueOptions(next).find((option) => option.path === key);
      if (!created) throw new Error("The new value could not be read back.");
      return created;
    },
    [ensureDraft, ensureTool, flushSaves, queryClient, saveFields],
  );

  return { values, addValue };
};
