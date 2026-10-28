import React from "react";
import { IconArrowDown, IconStarFilled } from "@tabler/icons-react";
import { REVIEWS_SECTION_ID } from "../../../constants/scenarioPage.constants";
import { formatRatingLabel } from "../../../utils/scenarioPage.utils";
import type { RatingChipProps } from "./RatingChip.types";

export const RatingChip: React.FC<RatingChipProps> = ({
  average,
  reviewCount,
}) => {
  if (reviewCount === 0) return null;

  return (
    <a
      href={`#${REVIEWS_SECTION_ID}`}
      aria-label={formatRatingLabel(average, reviewCount)}
      className="absolute right-6 top-6 z-10 hidden items-center gap-2 rounded-sm border border-border-subtle bg-surface-inset/80 px-3 py-1.5 font-mono text-xs backdrop-blur-sm transition hover:border-accent/40 hover:bg-surface-raised lg:inline-flex"
    >
      <IconStarFilled size={14} className="text-accent" aria-hidden="true" />
      <span className="font-semibold text-content">{average.toFixed(1)}</span>
      <span className="text-content-faint">· {reviewCount} reviews</span>
      <IconArrowDown size={14} stroke={1.5} className="text-content-faint" aria-hidden="true" />
    </a>
  );
};
