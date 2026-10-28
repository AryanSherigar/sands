import React from "react";
import type { GenreChipsProps } from "./GenreChips.types";

export const GenreChips: React.FC<GenreChipsProps> = ({ genreTags }) => {
  if (genreTags.length === 0) return null;
  const [primaryGenre, ...otherGenres] = genreTags;

  return (
    <ul className="flex flex-wrap items-center gap-2">
      <li className="inline-flex items-center gap-1.5 rounded-sm border border-accent/40 bg-accent/10 px-2.5 py-1 font-mono text-xs font-semibold uppercase tracking-wider text-accent">
        <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-accent" />
        {primaryGenre}
      </li>
      {otherGenres.map((genre) => (
        <li
          key={genre}
          className="rounded-sm border border-border-subtle bg-surface-raised/80 px-2.5 py-1 font-sans text-xs font-medium text-content-muted"
        >
          {genre}
        </li>
      ))}
    </ul>
  );
};
