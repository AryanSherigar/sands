import { useQuery } from "@tanstack/react-query";
import { getAllStrategySummaries } from "../api/simulation.api";
import { getStrategySummariesQueryKey } from "./useStrategySummaries";

export const getAllStrategySummariesQueryKey = (playthroughId?: string) =>
  [...getStrategySummariesQueryKey(playthroughId), "all"] as const;

export function useAllStrategySummaries(playthroughId?: string) {
  return useQuery({
    queryKey: getAllStrategySummariesQueryKey(playthroughId),
    queryFn: () => {
      if (!playthroughId) throw new Error("Playthrough ID is required");
      return getAllStrategySummaries(playthroughId);
    },
    enabled: Boolean(playthroughId),
    staleTime: 0,
  });
}
