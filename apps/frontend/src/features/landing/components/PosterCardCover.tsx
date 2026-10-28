import React from "react";
import { IconStarFilled } from "@tabler/icons-react";
import { MODE_LABELS } from "../constants/landing.constants";
import { resolveCoverImage } from "../utils/resolveCoverImage";
import { getGenreColor } from "../utils/getGenreColor";
import { PosterCardActions } from "./PosterCardActions";
import type { PosterCardCoverProps } from "./PosterCardCover.types";

export const PosterCardCover: React.FC<PosterCardCoverProps> = ({ scenario }) => {
  const primaryGenre = scenario.genre_tags[0];
  const rating = Number.parseFloat(scenario.rating_avg);
  const coverUrl = resolveCoverImage(scenario.cover_image_url, scenario.scenario_id);
  const genreColor = getGenreColor(primaryGenre);

  return (
    <div className="relative aspect-video w-full overflow-hidden bg-surface-inset">
      <img
        src={coverUrl}
        alt={scenario.title}
        loading="lazy"
        className="h-full w-full object-cover transition-transform duration-base ease-out group-hover:scale-105"
      />
      <div className="absolute inset-0 bg-linear-to-t from-surface-raised via-transparent to-transparent opacity-80" />
      <div className="absolute top-2 left-2 flex items-center gap-1.5">
        {primaryGenre && (
          <span
            className="rounded-sm bg-surface-inset/90 border border-border-subtle px-2 py-0.5 font-mono text-[11px]"
            style={{ color: genreColor }}
          >
            {primaryGenre}
          </span>
        )}
        <span className="rounded-sm bg-surface-inset/90 px-2 py-0.5 font-mono text-[11px] text-content-faint">
          {MODE_LABELS[scenario.mode]}
        </span>
      </div>
      {rating > 0 && (
        <div
          className="absolute bottom-2 right-2 flex items-center gap-1 rounded-sm bg-surface-inset/90 px-2 py-0.5 font-mono text-xs font-medium"
          style={{ color: genreColor }}
        >
          <IconStarFilled size={12} style={{ color: genreColor }} />
          {rating.toFixed(1)}
        </div>
      )}
      <PosterCardActions scenario={scenario} />
    </div>
  );
};
