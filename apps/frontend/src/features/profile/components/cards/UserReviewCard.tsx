import React from "react";
import { Link } from "react-router-dom";
import { MAX_RATING } from "../../constants/profileHeader.constants";
import type { UserReviewCardProps } from "./UserReviewCard.types";

export const UserReviewCard: React.FC<UserReviewCardProps> = ({ review }) => {
  const rating = Math.min(Math.max(review.rating, 0), MAX_RATING);
  const formattedDate = new Date(review.created_at).toLocaleDateString(
    undefined,
    { year: "numeric", month: "short", day: "numeric" },
  );

  return (
    <article className="rounded-md border border-border-subtle bg-surface-raised p-4">
      <div className="mb-3 flex flex-col justify-between gap-2 border-b border-border-subtle pb-3 sm:flex-row sm:items-center">
        <Link
          to={`/scenario/${review.scenario_id}`}
          className="font-display text-base font-semibold text-content hover:underline"
        >
          {review.scenario_title}
        </Link>
        <div className="flex items-center gap-3">
          <span aria-hidden="true" className="font-mono text-sm text-content">
            {"★".repeat(rating)}
            {"☆".repeat(MAX_RATING - rating)}
          </span>
          <span className="sr-only">Rated {rating} out of {MAX_RATING}</span>
          <span className="font-mono text-xs text-content-faint">
            {formattedDate}
          </span>
        </div>
      </div>
      <p className="text-sm text-content-muted">
        {review.review_text ?? "No written review."}
      </p>
    </article>
  );
};
