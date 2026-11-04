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
          className="inline-flex items-center gap-1.5 rounded-sm border-t bg-black/40 backdrop-blur-sm px-2.5 py-1 font-mono text-xs font-medium"
          style={{ borderTopColor: genreColor, color: genreColor }}
        >
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ backgroundColor: genreColor }}
          />
          {primaryGenre}
        </span>
      )}
      <span className="rounded-sm bg-black/40 px-2.5 py-1 font-mono text-xs text-white/85 backdrop-blur-sm">
        Interactive Fiction
      </span>
      <span className="rounded-sm bg-black/40 px-2.5 py-1 font-mono text-xs text-white/85 backdrop-blur-sm">
        {MODE_LABELS[mode]}
      </span>
      {showContentTag && (
        <span className="rounded-sm bg-black/40 px-2.5 py-1 font-mono text-xs text-white/85 backdrop-blur-sm">
          {contentTag}
        </span>
      )}
    </div>
  );
};
