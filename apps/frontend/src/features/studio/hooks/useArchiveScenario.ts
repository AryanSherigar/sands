import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateScenario } from "../api/scenarios.api";
import { MY_SCENARIOS_QUERY_KEY } from "../constants/studio-list";

export const useArchiveScenario = (scenarioId: string | null) => {
  const queryClient = useQueryClient();
  const archiveMutation = useMutation({
    mutationFn: () => {
      if (!scenarioId) throw new Error("Scenario ID is required.");
      return updateScenario(scenarioId, { status: "archived" });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [MY_SCENARIOS_QUERY_KEY] });
    },
  });

  return { archive: archiveMutation.mutate, isArchiving: archiveMutation.isPending };
};
