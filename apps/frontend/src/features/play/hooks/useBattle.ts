import { useQuery } from "@tanstack/react-query";
import { getBattle } from "../api/simulation.api";
import type { BattleView } from "../components/StrategyWarCouncil/StrategyWarCouncil.types";

export const getBattleQueryKey = (playthroughId?: string, battleId?: string) =>
  ["simulation-battle", playthroughId, battleId] as const;

export function useBattle(playthroughId: string, battleId: string, initialBattle?: BattleView) {
  return useQuery({
    queryKey: getBattleQueryKey(playthroughId, battleId),
    queryFn: () => getBattle(playthroughId, battleId),
    initialData: initialBattle,
    staleTime: 0,
  });
}
