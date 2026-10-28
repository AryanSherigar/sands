import { useQuery } from "@tanstack/react-query";
import { getCreatorStatsOverview } from "../api/stats.api";
import { STATS_STALE_TIME_MS } from "../constants/stats";
import type { StatsRange } from "../types/stats.types";

export const useCreatorStatsOverview = (range: StatsRange) =>
  useQuery({
    queryKey: ["stats", "overview", range],
    queryFn: () => getCreatorStatsOverview(range),
    staleTime: STATS_STALE_TIME_MS,
  });
