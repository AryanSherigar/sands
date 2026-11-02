import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { getTurnReport } from "../api/simulation.api";
import { deriveTurnReport } from "../lib/turnReportAdapter";
import { mergeTurnReport } from "../lib/turnReportMerge";
import { useStrategyPlayStore } from "../stores/strategyPlay.store";
import type { CampaignWorldView } from "../types/simulation.types";

export function useRestoredTurnReport(
  playthroughId: string | undefined,
  world: CampaignWorldView,
  regionNames: Record<string, string>,
): void {
  const completedTurn = world.turn - 1;
  const hasReport = useStrategyPlayStore((state) => state.latestReport !== null);
  const { data: apiReport } = useQuery({
    queryKey: ["simulation-turn-report", playthroughId, completedTurn],
    queryFn: () => getTurnReport(playthroughId ?? "", completedTurn),
    enabled: Boolean(playthroughId) && completedTurn >= 0 && !hasReport,
    staleTime: Infinity,
    retry: false,
  });

  useEffect(() => {
    if (!apiReport || useStrategyPlayStore.getState().latestReport) return;
    const estimated = deriveTurnReport(null, world, regionNames);
    useStrategyPlayStore
      .getState()
      .setLatestReport(mergeTurnReport(estimated, apiReport, world, regionNames));
  }, [apiReport, world, regionNames]);
}
