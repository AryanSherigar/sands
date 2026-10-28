import type { QueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { getScenario } from "../api/scenarios.api";
import { EDIT_CONFLICT_CODE, HTTP_STATUS_CONFLICT } from "../constants/editGuard";
import { useStudioStore } from "../stores/studio.store";
import type { ScenarioResponse } from "../types/scenario.types";
import { applyScenarioEditStamp } from "./scenarioEditStamp";

interface GuardedWriteOptions {
  shouldRefreshStamp?: boolean;
}

const guardedScenarioIds = new Set<string>();
const writeQueues = new Map<string, Promise<unknown>>();

export const enableEditGuard = (scenarioId: string): void => {
  guardedScenarioIds.add(scenarioId);
};

export const disableEditGuard = (scenarioId: string): void => {
  guardedScenarioIds.delete(scenarioId);
  writeQueues.delete(scenarioId);
};

export const isEditConflictError = (error: unknown): boolean =>
  isAxiosError(error) &&
  error.response?.status === HTTP_STATUS_CONFLICT &&
  (error.response.data as { code?: string } | undefined)?.code ===
    EDIT_CONFLICT_CODE;

const readCachedStamp = (
  queryClient: QueryClient,
  scenarioId: string,
): string | undefined =>
  queryClient.getQueryData<ScenarioResponse>(["scenario", scenarioId])
    ?.content_edited_at;

export const refreshEditStamp = async (
  queryClient: QueryClient,
  scenarioId: string,
): Promise<void> => {
  const latest = await getScenario(scenarioId);
  applyScenarioEditStamp(queryClient, scenarioId, latest.content_edited_at);
};

const readResultStamp = (result: unknown): string | undefined => {
  if (typeof result !== "object" || result === null) return undefined;
  const stamp = (result as { scenario_content_edited_at?: unknown })
    .scenario_content_edited_at;
  return typeof stamp === "string" ? stamp : undefined;
};

const runOne = async <T>(
  queryClient: QueryClient,
  scenarioId: string,
  write: (stamp: string | undefined) => Promise<T>,
  options: GuardedWriteOptions,
): Promise<T> => {
  try {
    const result = await write(readCachedStamp(queryClient, scenarioId));
    applyScenarioEditStamp(queryClient, scenarioId, readResultStamp(result));
    if (options.shouldRefreshStamp) await refreshEditStamp(queryClient, scenarioId);
    return result;
  } catch (error) {
    if (isEditConflictError(error)) useStudioStore.getState().setHasEditConflict(true);
    throw error;
  }
};

export const runGuardedWrite = <T>(
  queryClient: QueryClient,
  scenarioId: string,
  write: (stamp: string | undefined) => Promise<T>,
  options: GuardedWriteOptions = {},
): Promise<T> => {
  if (!guardedScenarioIds.has(scenarioId)) return write(undefined);
  const previous = writeQueues.get(scenarioId) ?? Promise.resolve();
  const next = previous
    .catch(() => undefined)
    .then(() => runOne(queryClient, scenarioId, write, options));
  writeQueues.set(scenarioId, next);
  return next;
};

export const waitForPendingWrites = async (scenarioId: string): Promise<void> => {
  await writeQueues.get(scenarioId)?.catch(() => undefined);
};

export const withEditStamp = <T extends { expected_content_edited_at?: string }>(
  payload: T,
  stamp: string | undefined,
): T => {
  if (!stamp || payload.expected_content_edited_at) return payload;
  return { ...payload, expected_content_edited_at: stamp };
};
