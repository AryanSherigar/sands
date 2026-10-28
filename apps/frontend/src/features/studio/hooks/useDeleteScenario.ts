import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteScenario } from "../api/scenarios.api";
import { MY_SCENARIOS_QUERY_KEY } from "../constants/studio-list";

export const useDeleteScenario = () => {
  const queryClient = useQueryClient();
  const deleteMutation = useMutation({
    mutationFn: (scenarioId: string) => deleteScenario(scenarioId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [MY_SCENARIOS_QUERY_KEY] });
    },
  });

  return { deleteScenario: deleteMutation.mutateAsync };
};
