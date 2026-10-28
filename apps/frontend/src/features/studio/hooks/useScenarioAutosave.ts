import { QueryClient, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { logEvent } from "@/shared/lib/logger";
import { updateScenario } from "../api/scenarios.api";
import { SCENARIO_AUTOSAVE_DEBOUNCE_MS } from "../constants/guideLimits";
import { SCENARIO_QUERY_KEY } from "../constants/studioScenario";
import { runGuardedWrite, withEditStamp } from "../lib/editGuard";
import {
  buildScenarioUpdate,
  hasFirstWord,
  isEmptyPatch,
  mergeScenarioPatches,
  subtractScenarioPatch,
} from "../lib/scenarioPatch";
import { useStudioStore } from "../stores/studio.store";
import type { ScenarioResponse } from "../types/scenario.types";
import type { ScenarioFieldsPatch } from "../types/scenarioPatch.types";

type CreateDraft = (seed: ScenarioFieldsPatch) => Promise<ScenarioResponse>;

const writePatch = (
  queryClient: QueryClient,
  scenarioId: string,
  patch: ScenarioFieldsPatch,
): Promise<ScenarioResponse> =>
  runGuardedWrite(queryClient, scenarioId, async (stamp) => {
    const cached = queryClient.getQueryData<ScenarioResponse>([
      SCENARIO_QUERY_KEY,
      scenarioId,
    ]);
    const update = buildScenarioUpdate(patch, cached?.world_data ?? {});
    const saved = await updateScenario(scenarioId, withEditStamp(update, stamp));
    queryClient.setQueryData([SCENARIO_QUERY_KEY, scenarioId], saved);
    return saved;
  });

export const useScenarioAutosave = (
  scenarioId: string | null,
  createDraft: CreateDraft,
) => {
  const queryClient = useQueryClient();
  const setSaveState = useStudioStore((state) => state.setSaveState);
  const [hasError, setHasError] = useState(false);
  const pendingRef = useRef<ScenarioFieldsPatch>({});
  const failedRef = useRef<ScenarioFieldsPatch>({});
  const scenarioIdRef = useRef(scenarioId);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isCreatingRef = useRef(false);

  useEffect(() => {
    scenarioIdRef.current = scenarioId ?? scenarioIdRef.current;
  }, [scenarioId]);

  const clearTimer = useCallback((): void => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
  }, []);

  const flush = useCallback(async (): Promise<boolean> => {
    const id = scenarioIdRef.current;
    const patch = mergeScenarioPatches(failedRef.current, pendingRef.current);
    if (isEmptyPatch(patch)) return true;
    if (!id) return false;
    pendingRef.current = {};
    clearTimer();
    setSaveState(true);
    try {
      await writePatch(queryClient, id, patch);
      failedRef.current = subtractScenarioPatch(failedRef.current, patch);
      setHasError(!isEmptyPatch(failedRef.current));
      setSaveState(false, new Date());
      return isEmptyPatch(failedRef.current);
    } catch (error) {
      failedRef.current = mergeScenarioPatches(failedRef.current, patch);
      setHasError(true);
      setSaveState(false);
      logEvent("warning", "scenario_autosave_failed", { error: String(error) });
      return false;
    }
  }, [clearTimer, queryClient, setSaveState]);

  const schedule = useCallback((): void => {
    clearTimer();
    timerRef.current = setTimeout(() => void flush(), SCENARIO_AUTOSAVE_DEBOUNCE_MS);
  }, [clearTimer, flush]);

  const startDraft = useCallback(async (): Promise<void> => {
    if (isCreatingRef.current || !hasFirstWord(pendingRef.current)) return;
    isCreatingRef.current = true;
    const seed = pendingRef.current;
    pendingRef.current = {};
    setSaveState(true);
    try {
      const created = await createDraft(seed);
      scenarioIdRef.current = created.scenario_id;
      setHasError(false);
      setSaveState(false, new Date());
    } catch (error) {
      pendingRef.current = mergeScenarioPatches(seed, pendingRef.current);
      setHasError(true);
      setSaveState(false);
      logEvent("warning", "scenario_draft_create_failed", { error: String(error) });
    } finally {
      isCreatingRef.current = false;
    }
    if (scenarioIdRef.current && !isEmptyPatch(pendingRef.current)) schedule();
  }, [createDraft, schedule, setSaveState]);

  const save = useCallback(
    (patch: ScenarioFieldsPatch): void => {
      pendingRef.current = mergeScenarioPatches(pendingRef.current, patch);
      if (scenarioIdRef.current) schedule();
      else void startDraft();
    },
    [schedule, startDraft],
  );

  const retry = useCallback((): void => {
    pendingRef.current = mergeScenarioPatches(failedRef.current, pendingRef.current);
    failedRef.current = {};
    if (scenarioIdRef.current) void flush();
    else void startDraft();
  }, [flush, startDraft]);

  useEffect(() => () => void flush(), [flush]);

  return { save, retry, flush, hasError };
};
