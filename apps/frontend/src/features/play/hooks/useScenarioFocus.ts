import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchScenarioDetail,
  toggleBookmarkApi,
  fetchPublicPlaythroughs,
} from "../api/scenarioFocus.api";
import { mockScenarios } from "../mock/scenarios";
import {
  ScenarioDetailResponse,
  ScenarioMock,
} from "../types/scenario";
import { useScenarioReviews } from "./useScenarioReviews";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";

export const useScenarioFocus = (scenarioId: string | undefined) => {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const requireAuthToSave = useRequireAuth("save");
  const reviews = useScenarioReviews(scenarioId);

  const scenarioQuery = useQuery({
    queryKey: ["scenario-detail", scenarioId],
    queryFn: async (): Promise<ScenarioDetailResponse> => {
      if (!scenarioId) throw new Error("Scenario ID is required");
      try {
        return await fetchScenarioDetail(scenarioId);
      } catch (error) {
        // NOTE: Dev-only fallback for browsing mock IDs locally; never served in
        // production, where a fetch failure must surface as a real error.
        if (!import.meta.env.DEV) throw error;

        const mockItem = mockScenarios.find(
          (item: ScenarioMock) => item.id === scenarioId,
        );
        if (mockItem) {
          return {
            scenario_id: mockItem.id,
            creator_id: "mock-creator-id",
            creator_display_name: mockItem.author,
            title: mockItem.title,
            logline: mockItem.logline,
            mode: mockItem.mode ?? "newbie",
            strategy_document: mockItem.strategy_document,
            status: "published",
            genre_tags: [mockItem.genre],
            complexity_tier: "newbie",
            player_count_support: "solo",
            estimated_playtime: "30-45 mins",
            playtime_bucket: "short",
            is_mature: false,
            cover_image_url: mockItem.coverImageUrl,
            content_tag: "PG-13",
            play_count: mockItem.playerCount,
            rating_avg: mockItem.rating.toString(),
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            is_bookmarked: false,
            can_review: false,
            world_data: {
              lore: "Deep in the forgotten realms, dark mysteries await brave adventurers. Uncover hidden secrets and brave dangerous hazards in this immersive text experience.",
            },
            setup_schema: mockItem.setupInputs || [],
          };
        }
        throw new Error("Scenario not found");
      }
    },
    enabled: Boolean(scenarioId),
  });

  const playthroughsQuery = useQuery({
    queryKey: ["scenario-public-playthroughs", scenarioId],
    queryFn: () => {
      if (!scenarioId) throw new Error("Scenario ID is required");
      return fetchPublicPlaythroughs(scenarioId);
    },
    enabled: Boolean(scenarioId),
  });

  const bookmarkMutation = useMutation({
    mutationFn: async () => {
      if (!scenarioId) return;
      return await toggleBookmarkApi(scenarioId);
    },
    onSuccess: (data) => {
      if (!data) return;
      queryClient.setQueryData(
        ["scenario-detail", scenarioId],
        (old: ScenarioDetailResponse | undefined) =>
          old ? { ...old, is_bookmarked: data.is_bookmarked } : old,
      );
    },
  });

  const handleToggleBookmark = async (): Promise<void> => {
    if (!(await requireAuthToSave())) return;
    bookmarkMutation.mutate();
  };

  const isBookmarked = Boolean(scenarioQuery.data?.is_bookmarked);

  return {
    scenario: scenarioQuery.data,
    isLoading: scenarioQuery.isLoading,
    isError: scenarioQuery.isError,
    ...reviews,
    publicPlaythroughs: playthroughsQuery.data || [],
    isPlaythroughsError: playthroughsQuery.isError,
    refetchPlaythroughs: () => void playthroughsQuery.refetch(),
    isBookmarked,
    toggleBookmark: handleToggleBookmark,
    isTogglingBookmark: bookmarkMutation.isPending,
    currentUser: user,
  };
};
