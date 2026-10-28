import { useInfiniteQuery } from "@tanstack/react-query";
import { listMyScenarios } from "../api/myScenarios.api";
import {
  MY_SCENARIOS_QUERY_KEY,
  STUDIO_PAGE_SIZE,
  STUDIO_PUBLISHING_POLL_MS,
  STUDIO_STALE_TIME_MS,
} from "../constants/studio-list";
import type {
  MyScenarioListResponse,
  MyScenarioSummary,
  ScenarioStatusCounts,
  StudioTab,
} from "../types/scenario.types";
import { parseNextOffset } from "@/shared/lib/parseNextOffset";

export interface UseMyScenariosResult {
  items: MyScenarioSummary[];
  statusCounts: ScenarioStatusCounts | null;
  isLoading: boolean;
  isError: boolean;
  isFetchingNextPage: boolean;
  isNextPageError: boolean;
  hasNextPage: boolean;
  fetchNextPage: () => void;
  refetch: () => void;
}

const hasPublishingRow = (pages: MyScenarioListResponse[] | undefined): boolean =>
  (pages ?? []).some((page) =>
    page.items.some((item) => item.status === "publishing"),
  );

export const useMyScenarios = (
  tab: StudioTab,
  query: string,
): UseMyScenariosResult => {
  const result = useInfiniteQuery({
    queryKey: [MY_SCENARIOS_QUERY_KEY, { tab, query }],
    queryFn: ({ pageParam }) =>
      listMyScenarios({
        tab,
        query,
        limit: STUDIO_PAGE_SIZE,
        offset: pageParam,
      }),
    initialPageParam: 0,
    getNextPageParam: parseNextOffset,
    staleTime: STUDIO_STALE_TIME_MS,
    refetchInterval: (state) =>
      hasPublishingRow(state.state.data?.pages) ? STUDIO_PUBLISHING_POLL_MS : false,
  });

  const pages = result.data?.pages ?? [];
  return {
    items: pages.flatMap((page) => page.items),
    statusCounts: pages[0]?.status_counts ?? null,
    isLoading: result.isLoading,
    isError: result.isError && pages.length === 0,
    isFetchingNextPage: result.isFetchingNextPage,
    isNextPageError: result.isFetchNextPageError,
    hasNextPage: result.hasNextPage,
    fetchNextPage: () => void result.fetchNextPage(),
    refetch: () => void result.refetch(),
  };
};
