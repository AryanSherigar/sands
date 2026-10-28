import React from "react";
import { MODE_LABELS } from "../constants/landing.constants";
import { getGenreColor } from "../utils/getGenreColor";
import type { HeroBadgesProps } from "./HeroBadges.types";

export const HeroBadges: React.FC<HeroBadgesProps> = ({
  primaryGenre,
  mode,
  contentTag,
}) => {
  const showContentTag = Boolean(contentTag && contentTag !== primaryGenre);
  const genreColor = getGenreColor(primaryGenre);

  return (
    <div className="mb-2.5 flex flex-wrap items-center gap-1.5">
      {primaryGenre && (
        <span
          className="inline-flex items-center gap-1.5 rounded-sm border-t bg-surface-raised/90 px-2.5 py-1 font-mono text-xs font-medium"
          style={{ borderTopColor: genreColor, color: genreColor }}
        >
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ backgroundColor: genreColor }}
          />
          {primaryGenre}
        </span>
      )}
      <span className="rounded-sm bg-surface-raised/80 px-2.5 py-1 font-mono text-xs text-content-muted">
        Interactive Fiction
      </span>
      <span className="rounded-sm bg-surface-raised/80 px-2.5 py-1 font-mono text-xs text-content-muted">
        {MODE_LABELS[mode]}
      </span>
      {showContentTag && (
        <span className="rounded-sm bg-surface-raised/80 px-2.5 py-1 font-mono text-xs text-content-muted">
          {contentTag}
        </span>
      )}
    </div>
  );
};
