import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
import { acceptCommand, cancelCommand, checkCommand } from "../api/simulation.api";
import { buildOperationGuard } from "../lib/operationGuard";
import { parseSimulationError } from "../lib/simulationError";
import type { CampaignWorldView, StrategyOrder } from "../types/simulation.types";
import { getStrategySummariesQueryKey } from "./useStrategySummaries";

const MISSING_PLAYTHROUGH_MESSAGE = "Playthrough ID is required";
const MISSING_WORLD_MESSAGE = "World state is not loaded yet";

export const getWorldQueryKey = (playthroughId?: string) =>
  ["simulation-world", playthroughId] as const;

export function readCachedWorld(
  queryClient: QueryClient,
  playthroughId: string,
): CampaignWorldView {
  const world = queryClient.getQueryData<CampaignWorldView>(getWorldQueryKey(playthroughId));
  if (!world) throw new Error(MISSING_WORLD_MESSAGE);
  return world;
}

export function useSimulationCommands(playthroughId?: string) {
  const queryClient = useQueryClient();

  const invalidateWorld = () => {
    void queryClient.invalidateQueries({ queryKey: getWorldQueryKey(playthroughId) });
    void queryClient.invalidateQueries({ queryKey: getStrategySummariesQueryKey(playthroughId) });
  };

  const handleError = (error: unknown) => {
    if (parseSimulationError(error, "").isStaleWorld) invalidateWorld();
  };

  const requirePlaythroughId = (): string => {
    if (!playthroughId) throw new Error(MISSING_PLAYTHROUGH_MESSAGE);
    return playthroughId;
  };

  const acceptMutation = useMutation({
    mutationFn: (command: StrategyOrder) => {
      const id = requirePlaythroughId();
      const guard = buildOperationGuard(readCachedWorld(queryClient, id));
      return acceptCommand(id, command, guard);
    },
    onSuccess: invalidateWorld,
    onError: handleError,
  });

  const cancelMutation = useMutation({
    mutationFn: (commandId: string) => {
      const id = requirePlaythroughId();
      const guard = buildOperationGuard(readCachedWorld(queryClient, id));
      return cancelCommand(id, commandId, guard);
    },
    onSuccess: invalidateWorld,
    onError: handleError,
  });

  const check = (command: StrategyOrder) => checkCommand(requirePlaythroughId(), command);

  return { acceptMutation, cancelMutation, check };
}
