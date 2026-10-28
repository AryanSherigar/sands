import React from "react";
import {
  DEFAULT_GENRE_DOT_CLASS,
  GENRE_DOT_CLASSES,
} from "../../constants/discover.constants";
import type { GenreChipProps } from "./GenreChip.types";

export const GenreChip: React.FC<GenreChipProps> = ({ genre }) => (
  <span className="inline-flex items-center gap-1.5 rounded-sm bg-surface px-2 py-0.5 font-mono text-xs text-content-muted">
    <span
      aria-hidden="true"
      className={`h-2 w-2 rounded-full ${GENRE_DOT_CLASSES[genre] ?? DEFAULT_GENRE_DOT_CLASS}`}
    />
    {genre}
  </span>
);
