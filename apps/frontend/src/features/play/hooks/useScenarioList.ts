import { useInfiniteQuery } from "@tanstack/react-query";
import { fetchScenarios } from "@/shared/api/scenarios.api";
import type {
  ScenarioSummaryResponse,
} from "@/shared/types/scenarioSummary.types";
import {
  DISCOVER_PAGE_SIZE,
  DISCOVER_STALE_TIME_MS,
} from "../constants/discover.constants";
import type { DiscoverFilters } from "../types/discover.types";
import { toScenarioApiParams } from "../utils/discoverFilters";
import { parseNextOffset } from "@/shared/lib/parseNextOffset";

export const SCENARIO_LIST_QUERY_KEY = "scenario-list";

export interface UseScenarioListResult {
  items: ScenarioSummaryResponse[];
  totalCount: number;
  isLoading: boolean;
  isError: boolean;
  isFetchingNextPage: boolean;
  hasNextPage: boolean;
  fetchNextPage: () => void;
  refetch: () => void;
}

export const useScenarioList = (
  filters: DiscoverFilters,
): UseScenarioListResult => {
  const apiParams = toScenarioApiParams(filters);
  const query = useInfiniteQuery({
    queryKey: [SCENARIO_LIST_QUERY_KEY, apiParams],
    queryFn: ({ pageParam }) =>
      fetchScenarios({ ...apiParams, limit: DISCOVER_PAGE_SIZE, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: parseNextOffset,
    staleTime: DISCOVER_STALE_TIME_MS,
  });

  const pages = query.data?.pages ?? [];
  return {
    items: pages.flatMap((page) => page.items),
    totalCount: pages[0]?.total_count ?? 0,
    isLoading: query.isLoading,
    isError: query.isError,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: query.hasNextPage,
    fetchNextPage: () => void query.fetchNextPage(),
    refetch: () => void query.refetch(),
  };
};
