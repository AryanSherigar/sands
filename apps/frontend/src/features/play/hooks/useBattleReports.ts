import { useQuery } from "@tanstack/react-query";
import { listBattleReports } from "../api/simulation.api";

export const getBattleReportsQueryKey = (playthroughId?: string, battleId?: string) =>
  ["simulation-battle-reports", playthroughId, battleId] as const;

export function useBattleReports(playthroughId: string, battleId: string) {
  return useQuery({
    queryKey: getBattleReportsQueryKey(playthroughId, battleId),
    queryFn: () => listBattleReports(playthroughId, battleId),
    staleTime: 0,
  });
}
