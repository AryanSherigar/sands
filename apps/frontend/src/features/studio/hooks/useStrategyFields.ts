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
  const inFlight = useRef<Promise<boolean>>(Promise.resolve(true));
  const writeDocument = useCallback(async (): Promise<void> => {
    // NOTE: the map is saved by its own endpoint, so overlay edits on the cached server document.
    const cached = queryClient.getQueryData<ScenarioResponse>([SCENARIO_QUERY_KEY, scenarioId]);
    const baseDocument = cached?.strategy_document ?? scenario.strategy_document ?? {};
    const saved = await updateScenario(scenarioId, {
      strategy_document: applyStrategyFields(baseDocument, latestFields.current),
    });
    queryClient.setQueryData([SCENARIO_QUERY_KEY, scenarioId], saved);
  }, [queryClient, scenario.strategy_document, scenarioId]);

  const saveUntilClean = useCallback(async (): Promise<boolean> => {
    while (isDirty.current) {
      if (timer.current) clearTimeout(timer.current);
      timer.current = null;
      isDirty.current = false;
      setSaveState("saving");
      try {
        await writeDocument();
      } catch {
        isDirty.current = true;
        setSaveState("failed");
        return false;
      }
    }
    setSaveState("saved");
    return true;
  }, [writeDocument]);

  const save = useCallback((): Promise<boolean> => {
    // NOTE: saves are chained so a slow earlier response can never overwrite a newer document.
    const next = inFlight.current.then(() => saveUntilClean());
    inFlight.current = next;
    return next;
  }, [saveUntilClean]);

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
