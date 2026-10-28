import { useMutation, useQueryClient } from "@tanstack/react-query";
import { acceptCommand, advanceBattles } from "../api/simulation.api";
import { buildOperationGuard } from "../lib/operationGuard";
import { parseSimulationError } from "../lib/simulationError";
import type { BattleControlCommand, CampaignWorldView } from "../types/simulation.types";
import { getWorldQueryKey, readCachedWorld } from "./useSimulationCommands";
import { getStrategySummariesQueryKey } from "./useStrategySummaries";

export function useBattleControl(playthroughId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: async (command: BattleControlCommand) => {
      const world = readCachedWorld(queryClient, playthroughId);
      const response = await acceptCommand(playthroughId, command, buildOperationGuard(world));
      queryClient.setQueryData<CampaignWorldView>(getWorldQueryKey(playthroughId), { ...world, ...response });
      const hasControlledBattle = response.battles.some((battle) => battle.control_mode === "player" && battle.status !== "resolved");
      if (command.kind === "delegate_battle" && response.status === "awaiting_commands" && !hasControlledBattle) {
        return advanceBattles(playthroughId, buildOperationGuard(response));
      }
      return response;
    },
    onSuccess: (response) => {
      queryClient.setQueryData<CampaignWorldView>(getWorldQueryKey(playthroughId), (world) => world && { ...world, ...response });
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: getWorldQueryKey(playthroughId) });
      void queryClient.invalidateQueries({ queryKey: getStrategySummariesQueryKey(playthroughId) });
    },
  });
  const errorInfo = mutation.error ? parseSimulationError(mutation.error, "Could not save battle choice. Refresh and try again.") : null;
  return { choose: mutation.mutate, isPending: mutation.isPending, errorInfo };
}
