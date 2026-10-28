import React, { useState } from "react";
import { FALLBACK_COVER_IMAGE_URLS } from "../constants/landing.constants";
import { getGenreColor } from "../utils/getGenreColor";
import type { ContinueCardThumbnailProps } from "./ContinueCardThumbnail.types";

export const ContinueCardThumbnail: React.FC<ContinueCardThumbnailProps> = ({
  coverUrl,
  genre,
}) => {
  const [hasError, setHasError] = useState(false);
  const genreColor = getGenreColor(genre);

  return (
    <div className="relative aspect-video w-full shrink-0 overflow-hidden bg-surface-inset sm:h-auto sm:w-48 sm:aspect-video">
      <img
        src={hasError ? FALLBACK_COVER_IMAGE_URLS[0] : coverUrl}
        alt=""
        loading="lazy"
        onError={() => setHasError(true)}
        className="h-full w-full object-cover transition-transform duration-base group-hover:scale-105"
      />
      <div className="absolute left-2.5 top-2.5">
        <span
          className="rounded-sm border border-border-subtle bg-surface-inset/90 px-2 py-0.5 font-mono text-[11px] font-medium"
          style={{ color: genreColor }}
        >
          {genre}
        </span>
      </div>
    </div>
  );
};
