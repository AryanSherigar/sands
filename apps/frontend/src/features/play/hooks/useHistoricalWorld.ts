import { useQuery } from "@tanstack/react-query";
import { getHistoricalWorld } from "../api/simulation.api";

export function useHistoricalWorld(playthroughId: string | undefined, turn: number | null) {
  return useQuery({
    queryKey: ["simulation-history", playthroughId, turn],
    queryFn: () => getHistoricalWorld(playthroughId ?? "", turn ?? 0),
    enabled: Boolean(playthroughId) && turn !== null,
    staleTime: Infinity,
    retry: false,
  });
}
