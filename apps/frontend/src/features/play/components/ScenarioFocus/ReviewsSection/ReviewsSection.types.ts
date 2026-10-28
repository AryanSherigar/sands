import type {
  RatingCount,
  ScenarioReviewResponse,
} from "../../../types/scenario";

export interface ReviewsSectionProps {
  reviews: ScenarioReviewResponse[];
  ownReview: ScenarioReviewResponse | null;
  totalReviews: number;
  averageRating: number;
  ratingCounts: RatingCount[];
  hasMoreReviews: boolean;
  isLoadingMoreReviews: boolean;
  canReview: boolean;
  isSignedIn: boolean;
  isError: boolean;
  isSubmittingReview: boolean;
  onLoadMore: () => void;
  onRetry: () => void;
  onRequestSignIn: () => void;
  onSubmitReview: (data: {
    rating: number;
    comment?: string;
  }) => Promise<unknown>;
}
