import React from "react";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { useScenarioEndings } from "../../../hooks/useScenarioEndings";
import { ContentTagList } from "../ContentTagList/ContentTagList";
import { EndingsSummary } from "../EndingsSummary/EndingsSummary";
import { ReviewsSection } from "../ReviewsSection/ReviewsSection";
import { ScenarioLoreSection } from "../ScenarioLoreSection";
import { SetupPreview } from "../SetupPreview/SetupPreview";
import type { ScenarioContentColumnProps } from "./ScenarioContentColumn.types";

export const ScenarioContentColumn: React.FC<ScenarioContentColumnProps> = ({
  scenario,
  focus,
}) => {
  const { endings, isEndingsError, refetchEndings } = useScenarioEndings(
    scenario.scenario_id,
  );
  const requireAuthToReview = useRequireAuth("review");

  return (
    <div className="space-y-10">
      <ScenarioLoreSection scenario={scenario} />
      <ContentTagList scenario={scenario} />
      <SetupPreview setupSchema={scenario.setup_schema ?? []} />
      <EndingsSummary
        endings={endings}
        isError={isEndingsError}
        onRetry={refetchEndings}
      />
      <ReviewsSection
        reviews={focus.reviews}
        ownReview={focus.ownReview}
        totalReviews={focus.totalReviews}
        averageRating={focus.averageRating}
        ratingCounts={focus.ratingCounts}
        hasMoreReviews={focus.hasMoreReviews}
        isLoadingMoreReviews={focus.isLoadingMoreReviews}
        canReview={Boolean(scenario.can_review)}
        isSignedIn={Boolean(focus.currentUser)}
        isError={focus.isReviewsError}
        isSubmittingReview={focus.isSubmittingReview}
        onLoadMore={focus.loadMoreReviews}
        onRetry={focus.refetchReviews}
        onRequestSignIn={() => void requireAuthToReview()}
        onSubmitReview={focus.submitReview}
      />
    </div>
  );
};
