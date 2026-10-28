import React from "react";
import { RATING_MAX } from "../../constants/stats";
import type { ReviewListProps } from "./ReviewList.types";

export const ReviewList: React.FC<ReviewListProps> = ({ reviews, showScenario }) => {
  if (reviews.length === 0) {
    return (
      <p className="font-sans text-sm text-content-muted">No reviews in this period.</p>
    );
  }
  return (
    <ul className="flex flex-col divide-y divide-border-subtle">
      {reviews.map((review) => (
        <li
          key={`${review.scenario_id}-${review.created_at}-${review.author_display_name}`}
          className="flex flex-col gap-1 py-3"
        >
          <div className="flex items-center gap-2 font-sans text-sm">
            <span className="font-medium text-content">{review.author_display_name}</span>
            <span
              className="font-mono tabular-nums text-content-muted"
              aria-label={`Rated ${review.rating} out of ${RATING_MAX}`}
            >
              {review.rating}/{RATING_MAX}
            </span>
            {showScenario && (
              <span className="truncate text-content-faint">on {review.scenario_title}</span>
            )}
          </div>
          {review.comment && (
            <p className="font-sans text-sm text-content-muted">{review.comment}</p>
          )}
        </li>
      ))}
    </ul>
  );
};
