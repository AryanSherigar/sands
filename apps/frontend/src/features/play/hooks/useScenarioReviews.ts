import {
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import type { InfiniteData } from "@tanstack/react-query";
import { fetchScenarioReviews, submitScenarioReview } from "../api/scenarioFocus.api";
import { REVIEWS_PAGE_SIZE } from "../constants/scenarioPage.constants";
import type {
  ScenarioReviewListResponse,
  ScenarioReviewResponse,
} from "../types/scenario";
import {
  applySubmittedReview,
  withoutReview,
} from "../utils/scenarioPage.utils";

type ReviewPages = InfiniteData<ScenarioReviewListResponse, number>;

interface SubmitReviewInput {
  rating: number;
  comment?: string;
}

const getNextOffset = (
  lastPage: ScenarioReviewListResponse,
  allPages: ScenarioReviewListResponse[],
): number | undefined => {
  const loadedCount = allPages.reduce((sum, page) => sum + page.items.length, 0);
  return loadedCount < lastPage.total_count ? loadedCount : undefined;
};

const mergeSubmittedReview = (
  cached: ReviewPages | undefined,
  submitted: ScenarioReviewResponse,
): ReviewPages | undefined => {
  if (!cached) return cached;
  const [firstPage, ...laterPages] = cached.pages;
  return {
    ...cached,
    pages: [
      applySubmittedReview(firstPage, submitted),
      ...laterPages.map((page) => ({
        ...page,
        items: withoutReview(page.items, submitted.review_id),
      })),
    ],
  };
};

export const useScenarioReviews = (scenarioId: string | undefined) => {
  const queryClient = useQueryClient();
  const queryKey = ["scenario-reviews", scenarioId];

  const reviewsQuery = useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam }) => {
      if (!scenarioId) throw new Error("Scenario ID is required");
      return fetchScenarioReviews(scenarioId, REVIEWS_PAGE_SIZE, pageParam);
    },
    initialPageParam: 0,
    getNextPageParam: getNextOffset,
    enabled: Boolean(scenarioId),
  });

  const submitMutation = useMutation({
    mutationFn: ({ rating, comment }: SubmitReviewInput) => {
      if (!scenarioId) throw new Error("Scenario ID required");
      return submitScenarioReview(scenarioId, rating, comment);
    },
    onSuccess: (submitted) => {
      // NOTE: Merge the POST response into the cache directly. An immediate
      // refetch can land before the write is visible and silently keep stale
      // data on screen; the mutation response is the ground truth.
      queryClient.setQueryData<ReviewPages>(queryKey, (cached) =>
        mergeSubmittedReview(cached, submitted),
      );
      void queryClient.invalidateQueries({ queryKey });
      void queryClient.invalidateQueries({
        queryKey: ["scenario-detail", scenarioId],
      });
    },
  });

  const firstPage = reviewsQuery.data?.pages[0];
  const ownReview = firstPage?.own_review ?? null;
  const otherReviews = withoutReview(
    reviewsQuery.data?.pages.flatMap((page) => page.items) ?? [],
    ownReview?.review_id,
  );

  return {
    reviews: ownReview ? [ownReview, ...otherReviews] : otherReviews,
    ownReview,
    totalReviews: firstPage?.total_count ?? 0,
    averageRating: firstPage?.average_rating ?? 0,
    ratingCounts: firstPage?.rating_counts ?? [],
    isReviewsError: reviewsQuery.isError,
    refetchReviews: () => void reviewsQuery.refetch(),
    hasMoreReviews: Boolean(reviewsQuery.hasNextPage),
    isLoadingMoreReviews: reviewsQuery.isFetchingNextPage,
    loadMoreReviews: () => void reviewsQuery.fetchNextPage(),
    submitReview: submitMutation.mutateAsync,
    isSubmittingReview: submitMutation.isPending,
  };
};
