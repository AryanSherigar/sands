import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getScenarioTools, updateScenarioTools } from "../api/scenarioTools.api";
import {
  ScenarioToolsResponse,
  ScenarioToolsUpdate,
} from "../types/scenarioTools.types";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";

const scenarioToolsQueryKey = (scenarioId: string | null) => [
  "scenario-tools",
  scenarioId,
];

export const useScenarioTools = (scenarioId: string | null) => {
  const queryClient = useQueryClient();
  const queryKey = scenarioToolsQueryKey(scenarioId);

  const toolsQuery = useQuery<ScenarioToolsResponse, Error>({
    queryKey,
    queryFn: () => getScenarioTools(scenarioId as string),
    enabled: Boolean(scenarioId),
  });

  const updateMutation = useMutation<
    ScenarioToolsResponse,
    Error,
    ScenarioToolsUpdate
  >({
    mutationFn: (payload) => {
      if (!scenarioId) throw new Error("Scenario ID is required.");
      return updateScenarioTools(scenarioId, payload);
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKey, updated);
      queryClient.invalidateQueries({ queryKey: ["scenario", scenarioId] });
    },
  });

  return {
    tools: toolsQuery.data ?? null,
    isLoading: toolsQuery.isLoading,
    updateTools: updateMutation.mutate,
    isUpdating: updateMutation.isPending,
    lastAutoEnabled: updateMutation.data?.auto_enabled ?? [],
    updateError: updateMutation.error
      ? extractErrorMessage(updateMutation.error, "Failed to update tools.")
      : null,
  };
};
