import { useQuery } from "@tanstack/react-query";
import { getCampaignWorld } from "../api/simulation.api";
import type { CampaignWorldView } from "../types/simulation.types";

export function useSimulationWorld(playthroughId?: string) {
  return useQuery<CampaignWorldView, Error>({
    queryKey: ["simulation-world", playthroughId],
    queryFn: () => {
      if (!playthroughId) throw new Error("Playthrough ID is required");
      return getCampaignWorld(playthroughId);
    },
    enabled: Boolean(playthroughId),
    staleTime: 0,
  });
}
