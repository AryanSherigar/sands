import React from "react";
import {
  DEFAULT_GENRE_DOT_CLASS,
  GENRE_DOT_CLASSES,
} from "../../constants/discover.constants";
import type { GenreCoverBadgeProps } from "./GenreCoverBadge.types";

export const GenreCoverBadge: React.FC<GenreCoverBadgeProps> = ({ genre }) => (
  <span className="absolute bottom-2 left-2 inline-flex items-center gap-1.5 rounded border border-border-subtle bg-surface-sunken/90 px-2 py-0.5 font-mono text-[11px] font-medium text-content backdrop-blur-xs">
    <span
      aria-hidden="true"
      className={`h-1.5 w-1.5 rounded-full ${GENRE_DOT_CLASSES[genre] ?? DEFAULT_GENRE_DOT_CLASS}`}
    />
    {genre}
  </span>
);
