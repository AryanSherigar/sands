import { useQuery } from "@tanstack/react-query";
import { getStrategyDispatches } from "../api/simulation.api";

export const getStrategyDispatchesQueryKey = (playthroughId?: string) =>
  ["strategy-dispatches", playthroughId] as const;

export function useStrategyDispatches(playthroughId?: string) {
  return useQuery({
    queryKey: getStrategyDispatchesQueryKey(playthroughId),
    queryFn: () => {
      if (!playthroughId) throw new Error("Playthrough ID is required");
      return getStrategyDispatches(playthroughId);
    },
    enabled: Boolean(playthroughId),
    staleTime: 0,
  });
}
