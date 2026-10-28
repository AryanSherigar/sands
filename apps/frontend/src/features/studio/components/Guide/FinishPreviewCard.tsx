import React from "react";
import { TypographicCover } from "@/shared/components/TypographicCover/TypographicCover";
import { getGenreAccentClass } from "@/shared/constants/genreAccent.constants";
import type { FinishPreviewCardProps } from "./Guide.types";

const COVER_ASPECT_CLASS = "aspect-3/4";

export const FinishPreviewCard: React.FC<FinishPreviewCardProps> = ({
  title,
  logline,
  coverImageUrl,
  primaryGenre,
}) => (
  <article
    aria-label="How your story will look"
    className="mx-auto flex w-full max-w-[220px] flex-col gap-2 rounded-xl border border-border-subtle p-2"
  >
    {coverImageUrl ? (
      <img
        src={coverImageUrl}
        alt=""
        className={`${COVER_ASPECT_CLASS} w-full rounded-lg border border-border-subtle bg-surface-inset object-cover`}
      />
    ) : (
      <TypographicCover title={title} primaryGenre={primaryGenre} className={COVER_ASPECT_CLASS} />
    )}
    <h3 className="line-clamp-2 font-display text-base font-semibold text-content">
      {title.trim() || "Untitled story"}
    </h3>
    {primaryGenre && (
      <span className={`text-micro text-accent ${getGenreAccentClass(primaryGenre)}`}>{primaryGenre}</span>
    )}
    {logline && <p className="line-clamp-3 text-meta text-content-muted">{logline}</p>}
  </article>
);
