import { useQuery } from "@tanstack/react-query";
import { getScenarioStats } from "../api/stats.api";
import { STATS_STALE_TIME_MS } from "../constants/stats";
import type { StatsRange } from "../types/stats.types";

export const useScenarioStats = (scenarioId: string, range: StatsRange) =>
  useQuery({
    queryKey: ["stats", "scenario", scenarioId, range],
    queryFn: () => getScenarioStats(scenarioId, range),
    enabled: scenarioId.length > 0,
    staleTime: STATS_STALE_TIME_MS,
  });
