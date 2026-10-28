import React from "react";
import { IconStar, IconUsers } from "@tabler/icons-react";
import {
  FALLBACK_COVER_IMAGE,
  RATING_FRACTION_DIGITS,
} from "../../constants/profileHeader.constants";
import type { ScenarioMiniCardProps } from "./ScenarioMiniCard.types";

const CHIP_CLASSES =
  "rounded-sm border border-border-subtle bg-surface-raised px-2 py-0.5 text-xs font-medium text-content-muted";

export const ScenarioMiniCard: React.FC<ScenarioMiniCardProps> = ({
  scenario,
  overlayAction,
  footerAction,
}) => {
  const genre = scenario.genre_tags[0];
  const cover = scenario.cover_image_url || FALLBACK_COVER_IMAGE;
  const rating = parseFloat(scenario.rating_avg).toFixed(
    RATING_FRACTION_DIGITS,
  );

  return (
    <article className="flex flex-col overflow-hidden rounded-md border border-border-subtle bg-surface-raised transition duration-fast hover:border-border-strong motion-reduce:transition-none">
      <div className="relative aspect-video w-full overflow-hidden bg-surface-inset">
        <img
          src={cover}
          alt={scenario.title}
          className="h-full w-full object-cover"
        />
        <div className="absolute left-3 top-3 flex gap-2">
          {genre && <span className={CHIP_CLASSES}>{genre}</span>}
          <span className={`${CHIP_CLASSES} capitalize`}>{scenario.mode}</span>
        </div>
        {overlayAction && (
          <div className="absolute right-3 top-3">{overlayAction}</div>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div>
          <h3 className="line-clamp-1 font-display text-lg font-semibold text-content">
            {scenario.title}
          </h3>
          {scenario.logline && (
            <p className="mt-1 line-clamp-2 text-sm text-content-muted">
              {scenario.logline}
            </p>
          )}
        </div>
        <div className="mt-auto flex items-center justify-between border-t border-border-subtle pt-3 text-xs text-content-muted">
          <div className="flex items-center gap-4 font-mono">
            <span className="flex items-center gap-1">
              <IconStar size={16} stroke={1.5} aria-hidden="true" />
              {rating}
            </span>
            <span className="flex items-center gap-1">
              <IconUsers size={16} stroke={1.5} aria-hidden="true" />
              {scenario.play_count}
            </span>
          </div>
          {footerAction}
        </div>
      </div>
    </article>
  );
};
