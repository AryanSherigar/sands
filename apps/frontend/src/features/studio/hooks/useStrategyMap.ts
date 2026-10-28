import { useQuery } from "@tanstack/react-query";
import type { MapDocument } from "@/shared/types/strategy-map.types";
import { getStrategyMap } from "../api/strategy.api";

export const STRATEGY_MAP_QUERY_KEY = "strategy-map";

export const useStrategyMap = (scenarioId: string) =>
  useQuery<MapDocument | null, Error>({
    queryKey: [STRATEGY_MAP_QUERY_KEY, scenarioId],
    queryFn: () => getStrategyMap(scenarioId),
    staleTime: 0,
  });
