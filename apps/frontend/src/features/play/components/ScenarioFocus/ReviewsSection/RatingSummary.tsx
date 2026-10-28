import React from "react";
import { formatRatingLabel } from "../../../utils/scenarioPage.utils";
import { ReviewStars } from "./ReviewStars";
import type { RatingSummaryProps } from "./RatingSummary.types";

const PROGRESS_CLASSES =
  "h-2 flex-1 appearance-none overflow-hidden rounded-full [&::-moz-progress-bar]:bg-accent [&::-webkit-progress-bar]:bg-surface-inset [&::-webkit-progress-value]:bg-accent";

export const RatingSummary: React.FC<RatingSummaryProps> = ({
  average,
  reviewCount,
  buckets,
}) => (
  <div className="grid grid-cols-1 items-center gap-6 rounded-md border border-border-subtle bg-surface-raised p-6 sm:grid-cols-[140px_1fr]">
    <div className="space-y-1 text-center sm:text-left">
      <p className="font-display text-5xl font-black tracking-tight text-content">
        {reviewCount > 0 ? average.toFixed(1) : "—"}
      </p>
      <div className="flex justify-center sm:justify-start">
        <ReviewStars value={Math.round(average)} size={18} />
      </div>
      <p className="font-sans text-xs text-content-faint">
        {formatRatingLabel(average, reviewCount)}
      </p>
    </div>
    <ul className="space-y-1.5 font-mono text-xs" aria-hidden="true">
      {buckets.map(({ stars, percent }) => (
        <li key={stars} className="flex items-center gap-3">
          <span className="w-7 text-content-muted">{stars} ★</span>
          <progress
            value={percent}
            max={100}
            className={PROGRESS_CLASSES}
          />
          <span className="w-9 text-right text-content-faint">{percent}%</span>
        </li>
      ))}
    </ul>
  </div>
);
