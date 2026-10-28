import { useCallback } from "react";
import {
  useMutation,
  useQueryClient,
  type InfiniteData,
} from "@tanstack/react-query";
import { toggleBookmarkApi } from "@/shared/api/scenarios.api";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { useToast } from "@/shared/hooks/useToast";
import { logEvent } from "@/shared/lib/logger";
import type {
  ScenarioListResponse,
  ScenarioSummaryResponse,
} from "@/shared/types/scenarioSummary.types";
import { SCENARIO_LIST_QUERY_KEY } from "./useScenarioList";

type ListCache = InfiniteData<ScenarioListResponse, number>;

function withBookmarkState(
  cache: ListCache | undefined,
  scenarioId: string,
  isBookmarked: boolean,
): ListCache | undefined {
  if (!cache) return cache;
  const mapItem = (item: ScenarioSummaryResponse): ScenarioSummaryResponse =>
    item.scenario_id === scenarioId
      ? { ...item, is_bookmarked: isBookmarked }
      : item;
  return {
    ...cache,
    pages: cache.pages.map((page) => ({ ...page, items: page.items.map(mapItem) })),
  };
}

export const useToggleSave = (): ((
  scenario: ScenarioSummaryResponse,
) => Promise<void>) => {
  const queryClient = useQueryClient();
  const showToast = useToast();
  const requireAuth = useRequireAuth("save");
  const mutation = useMutation({ mutationFn: toggleBookmarkApi });

  const applyState = useCallback(
    (scenarioId: string, isBookmarked: boolean): void => {
      queryClient.setQueriesData<ListCache>(
        { queryKey: [SCENARIO_LIST_QUERY_KEY] },
        (cache) => withBookmarkState(cache, scenarioId, isBookmarked),
      );
    },
    [queryClient],
  );

  return useCallback(
    async (scenario: ScenarioSummaryResponse): Promise<void> => {
      if (!(await requireAuth())) return;
      const nextState = !scenario.is_bookmarked;
      applyState(scenario.scenario_id, nextState);
      if (nextState) showToast("Saved", "success");
      try {
        await mutation.mutateAsync(scenario.scenario_id);
      } catch (error) {
        logEvent("warning", "discover_save_toggle_failed", { error: String(error) });
        applyState(scenario.scenario_id, !nextState);
        showToast("Couldn't update your saved stories. Try again.", "error");
      }
    },
    [applyState, mutation, requireAuth, showToast],
  );
};
