import type { QueryClient } from "@tanstack/react-query";
import type { ToolKey } from "@/shared/constants/scenario-tools";
import { getScenarioTools, updateScenarioTools } from "../api/scenarioTools.api";
import { SCENARIO_QUERY_KEY } from "../constants/studioScenario";
import { runGuardedWrite } from "./editGuard";
import type { ScenarioResponse } from "../types/scenario.types";
import type { ScenarioToolsResponse } from "../types/scenarioTools.types";

const SCENARIO_TOOLS_QUERY_KEY = "scenario-tools";

export class ToolsRequireAdvancedModeError extends Error {
  constructor() {
    super("Tools can only be changed while Advanced mode is on.");
    this.name = "ToolsRequireAdvancedModeError";
  }
}

const writeQueues = new Map<string, Promise<unknown>>();

const runSerialized = <T>(scenarioId: string, task: () => Promise<T>): Promise<T> => {
  const previous = writeQueues.get(scenarioId) ?? Promise.resolve();
  const next = previous.catch(() => undefined).then(task);
  writeQueues.set(scenarioId, next);
  const release = (): void => {
    if (writeQueues.get(scenarioId) === next) writeQueues.delete(scenarioId);
  };
  next.then(release, release);
  return next;
};

const readCachedScenario = (queryClient: QueryClient, scenarioId: string): ScenarioResponse | undefined =>
  queryClient.getQueryData<ScenarioResponse>([SCENARIO_QUERY_KEY, scenarioId]);

const readEnabledTools = async (
  queryClient: QueryClient,
  scenarioId: string,
): Promise<string[]> => {
  const cached = readCachedScenario(queryClient, scenarioId);
  if (cached?.mode !== "master") throw new ToolsRequireAdvancedModeError();
  if (cached.enabled_tools) return cached.enabled_tools;
  return (await getScenarioTools(scenarioId)).enabled_tools;
};

const applyEnabledTools = (
  queryClient: QueryClient,
  scenarioId: string,
  updated: ScenarioToolsResponse,
): void => {
  queryClient.setQueryData<ScenarioResponse | undefined>(
    [SCENARIO_QUERY_KEY, scenarioId],
    (scenario) => (scenario ? { ...scenario, enabled_tools: updated.enabled_tools } : scenario),
  );
  queryClient.setQueryData([SCENARIO_TOOLS_QUERY_KEY, scenarioId], updated);
};

const writeEnabledTools = (
  queryClient: QueryClient,
  scenarioId: string,
  enabledTools: string[],
): Promise<void> =>
  runGuardedWrite(
    queryClient,
    scenarioId,
    async () => {
      const updated = await updateScenarioTools(scenarioId, { enabled_tools: enabledTools });
      applyEnabledTools(queryClient, scenarioId, updated);
    },
    { shouldRefreshStamp: true },
  );

export const ensureToolEnabled = (
  queryClient: QueryClient,
  scenarioId: string,
  toolKey: ToolKey,
): Promise<void> =>
  runSerialized(scenarioId, async () => {
    const enabled = await readEnabledTools(queryClient, scenarioId);
    if (enabled.includes(toolKey)) return;
    await writeEnabledTools(queryClient, scenarioId, [...enabled, toolKey]);
  });

export const disableToolEnabled = (
  queryClient: QueryClient,
  scenarioId: string,
  toolKey: ToolKey,
): Promise<void> =>
  runSerialized(scenarioId, async () => {
    const enabled = await readEnabledTools(queryClient, scenarioId);
    if (!enabled.includes(toolKey)) return;
    await writeEnabledTools(
      queryClient,
      scenarioId,
      enabled.filter((key) => key !== toolKey),
    );
  });
