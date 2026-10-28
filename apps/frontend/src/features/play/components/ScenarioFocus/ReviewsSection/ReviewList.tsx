import React from "react";
import { ReviewStars } from "./ReviewStars";
import type { ReviewListProps } from "./ReviewList.types";

export const ReviewList: React.FC<ReviewListProps> = ({ reviews }) => (
  <ul className="space-y-3">
    {reviews.map((review) => (
      <li
        key={review.review_id}
        className="space-y-2 rounded-md border border-border-subtle bg-surface-raised p-4"
      >
        <div className="flex items-center justify-between gap-3">
          <span className="font-sans text-sm font-semibold text-content">
            {review.user_display_name}
          </span>
          <span className="flex items-center gap-2 font-mono text-xs text-content-faint">
            <ReviewStars value={review.rating} size={12} />
            <span className="sr-only">{review.rating} out of 5</span>
            {new Date(review.created_at).toLocaleDateString()}
          </span>
        </div>
        {review.comment && (
          <p className="font-sans text-sm leading-relaxed text-content-muted">
            {review.comment}
          </p>
        )}
      </li>
    ))}
  </ul>
);
