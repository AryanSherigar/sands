import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";
import { getRatingBuckets } from "../../../utils/scenarioPage.utils";
import { RatingSummary } from "./RatingSummary";
import { ReviewComposer } from "./ReviewComposer";
import { ReviewEligibility } from "./ReviewEligibility";
import { ReviewList } from "./ReviewList";
import type { ReviewsSectionProps } from "./ReviewsSection.types";

type ReviewsBodyProps = Omit<ReviewsSectionProps, "isError" | "onRetry">;

const NO_REVIEWS_COPY = "No reviews yet";

export const ReviewsBody: React.FC<ReviewsBodyProps> = ({
  reviews,
  ownReview,
  totalReviews,
  averageRating,
  ratingCounts,
  hasMoreReviews,
  isLoadingMoreReviews,
  canReview,
  isSignedIn,
  isSubmittingReview,
  onLoadMore,
  onRequestSignIn,
  onSubmitReview,
}) => {
  const isAlphaMode = useIsAlphaMode();
  const canCompose = canReview || Boolean(ownReview);

  return (
    <>
      <RatingSummary
        average={averageRating}
        reviewCount={totalReviews}
        buckets={getRatingBuckets(ratingCounts, totalReviews)}
      />
      {canCompose && !isAlphaMode && (
        <ReviewComposer
          key={ownReview?.review_id ?? "new"}
          existingReview={ownReview ?? undefined}
          isSubmitting={isSubmittingReview}
          onSubmit={onSubmitReview}
        />
      )}
      {!canCompose && !isAlphaMode && (
        <ReviewEligibility
          isSignedIn={isSignedIn}
          onRequestSignIn={onRequestSignIn}
        />
      )}
      {reviews.length === 0 && (
        <p className="font-sans text-sm text-content-faint">{NO_REVIEWS_COPY}</p>
      )}
      {reviews.length > 0 && <ReviewList reviews={reviews} />}
      {hasMoreReviews && (
        <Button
          type="button"
          variant="secondary"
          size="md"
          onClick={onLoadMore}
          disabled={isLoadingMoreReviews}
        >
          {isLoadingMoreReviews ? "Loading…" : "Show more"}
        </Button>
      )}
    </>
  );
};
