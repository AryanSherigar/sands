import React from "react";
import { GENRES } from "@/shared/constants/genres";
import type { QuickGenreChipsProps } from "./QuickGenreChips.types";

export const QuickGenreChips: React.FC<QuickGenreChipsProps> = ({
  selected,
  onToggle,
}) => (
  <ul className="flex gap-2 overflow-x-auto pb-2">
    {GENRES.map((genre) => {
      const isSelected = selected.includes(genre);
      return (
        <li key={genre} className="shrink-0">
          <button
            type="button"
            aria-pressed={isSelected}
            onClick={() => onToggle(genre)}
            className={`rounded-full border px-3 py-1 text-xs ${
              isSelected
                ? "border-accent bg-accent-subtle text-accent"
                : "border-border-subtle text-content-muted"
            }`}
          >
            {genre}
          </button>
        </li>
      );
    })}
  </ul>
);
