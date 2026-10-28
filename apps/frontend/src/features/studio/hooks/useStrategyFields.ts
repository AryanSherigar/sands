import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { updateScenario } from "../api/scenarios.api";
import { SCENARIO_QUERY_KEY } from "../constants/studioScenario";
import { STRATEGY_SAVE_DEBOUNCE_MS } from "../constants/strategyAuthoring";
import { applyStrategyFields, readStrategyFields } from "../lib/strategyDocument";
import type { ScenarioResponse } from "../types/scenario.types";
import type { StrategyFields } from "../types/strategyDocument.types";

export type StrategySaveState = "saved" | "saving" | "failed";

export const useStrategyFields = (scenario: ScenarioResponse) => {
  const queryClient = useQueryClient();
  const scenarioId = scenario.scenario_id;
  const [fields, setFields] = useState<StrategyFields>(() =>
    readStrategyFields(scenario.strategy_document ?? {}),
  );
  const [saveState, setSaveState] = useState<StrategySaveState>("saved");
  const latestFields = useRef(fields);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isDirty = useRef(false);

  const save = useCallback(async (): Promise<void> => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    if (!isDirty.current) return;
    isDirty.current = false;
    setSaveState("saving");
    // NOTE: the map is saved by its own endpoint, so overlay edits on the cached server document.
    const cached = queryClient.getQueryData<ScenarioResponse>([SCENARIO_QUERY_KEY, scenarioId]);
    const baseDocument = cached?.strategy_document ?? scenario.strategy_document ?? {};
    try {
      const saved = await updateScenario(scenarioId, {
        strategy_document: applyStrategyFields(baseDocument, latestFields.current),
      });
      queryClient.setQueryData([SCENARIO_QUERY_KEY, scenarioId], saved);
      setSaveState(isDirty.current ? "saving" : "saved");
    } catch {
      isDirty.current = true;
      setSaveState("failed");
    }
  }, [queryClient, scenario.strategy_document, scenarioId]);

  const edit = useCallback(
    (change: (current: StrategyFields) => StrategyFields): void => {
      latestFields.current = change(latestFields.current);
      setFields(latestFields.current);
      isDirty.current = true;
      setSaveState("saving");
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => void save(), STRATEGY_SAVE_DEBOUNCE_MS);
    },
    [save],
  );

  useEffect(
    () => () => {
      if (timer.current) void save();
    },
    [save],
  );

  return { fields, edit, flush: save, saveState };
};
