import React from "react";
import { getGenreAccentClass } from "@/shared/constants/genreAccent.constants";
import { cn } from "@/shared/lib/cn";
import type { TypographicCoverProps } from "./TypographicCover.types";

const UNTITLED_LABEL = "Untitled story";

export const TypographicCover: React.FC<TypographicCoverProps> = ({
  title,
  primaryGenre,
  className,
}) => {
  const displayTitle = title.trim() || UNTITLED_LABEL;
  const surfaceClasses = primaryGenre
    ? cn(getGenreAccentClass(primaryGenre), "bg-accent text-primary-contrast")
    : "border border-border-subtle bg-surface-raised text-content";

  return (
    <div
      role="img"
      aria-label={displayTitle}
      className={cn(
        "flex aspect-video w-full items-center justify-center overflow-hidden rounded-md p-6 text-center",
        surfaceClasses,
        className,
      )}
    >
      <span
        aria-hidden="true"
        className="line-clamp-3 font-display text-heading font-semibold break-words"
      >
        {displayTitle}
      </span>
    </div>
  );
};
