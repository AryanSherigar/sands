import React from "react";
import { useUserReviews } from "../../hooks/useUserReviews";
import { UserReviewCard } from "../cards/UserReviewCard";
import { TabEmptyState } from "../states/TabEmptyState";
import { TabErrorState } from "../states/TabErrorState";
import { TabSkeleton } from "../states/TabSkeleton";
import type { ReviewsTabProps } from "./ReviewsTab.types";

export const ReviewsTab: React.FC<ReviewsTabProps> = ({ userId }) => {
  const { data: reviews, isLoading, isError } = useUserReviews(userId);

  if (isLoading) return <TabSkeleton />;
  if (isError) return <TabErrorState message="Couldn't load reviews." />;

  const items = reviews ?? [];
  if (items.length === 0) return <TabEmptyState message="No reviews yet" />;

  return (
    <div className="space-y-3">
      {items.map((review) => (
        <UserReviewCard key={review.review_id} review={review} />
      ))}
    </div>
  );
};
