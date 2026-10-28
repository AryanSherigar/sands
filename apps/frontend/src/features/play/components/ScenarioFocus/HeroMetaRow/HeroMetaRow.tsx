import React from "react";
import {
  IconClock,
  IconPlayerPlay,
  IconStarFilled,
  IconTool,
} from "@tabler/icons-react";
import { REVIEWS_SECTION_ID } from "../../../constants/scenarioPage.constants";
import {
  formatRatingLabel,
  getComplexityLabel,
  getModeLabel,
} from "../../../utils/scenarioPage.utils";
import type { HeroMetaRowProps } from "./HeroMetaRow.types";

export const HeroMetaRow: React.FC<HeroMetaRowProps> = ({
  scenario,
  reviewCount,
  averageRating,
}) => (
  <ul className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-border-subtle/80 pt-3 font-mono text-xs text-content-muted">
    <li>
      <a
        href={`#${REVIEWS_SECTION_ID}`}
        aria-label={formatRatingLabel(averageRating, reviewCount)}
        className="flex items-center gap-1.5 text-content hover:underline"
      >
        <IconStarFilled size={14} className="text-accent" aria-hidden="true" />
        {reviewCount > 0 ? averageRating.toFixed(1) : "New"}
        {reviewCount > 0 && (
          <span className="text-content-faint">({reviewCount})</span>
        )}
      </a>
    </li>
    <li className="flex items-center gap-1">
      <IconPlayerPlay size={14} stroke={1.5} aria-hidden="true" />
      {scenario.play_count.toLocaleString()} plays
    </li>
    {scenario.estimated_playtime && (
      <>
        <li className="flex items-center gap-1">
          <IconClock size={14} stroke={1.5} aria-hidden="true" />
          {scenario.estimated_playtime}
        </li>
      </>
    )}
    <li className="flex items-center gap-1">
      <IconTool size={14} stroke={1.5} aria-hidden="true" />
      {getModeLabel(scenario.mode)} · {getComplexityLabel(scenario.complexity_tier)}
    </li>
  </ul>
);
