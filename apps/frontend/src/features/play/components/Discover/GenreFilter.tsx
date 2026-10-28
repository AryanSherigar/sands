import React from "react";
import { GENRES } from "@/shared/constants/genres";
import {
  DEFAULT_GENRE_DOT_CLASS,
  GENRE_DOT_CLASSES,
} from "../../constants/discover.constants";
import { FilterFieldset } from "./FilterFieldset";
import { FilterRow } from "./FilterRow";
import type { GenreFilterProps } from "./GenreFilter.types";

const ALL_GENRES_GROUP = "all-genres";

export const GenreFilter: React.FC<GenreFilterProps> = ({
  selected,
  onChange,
}) => {
  const handleToggle = (genre: string): void => {
    const isSelected = selected.includes(genre);
    onChange(
      isSelected ? selected.filter((item) => item !== genre) : [...selected, genre],
    );
  };

  return (
    <FilterFieldset legend="Genres">
      <FilterRow
        inputType="radio"
        name={ALL_GENRES_GROUP}
        label="All Genres"
        isChecked={selected.length === 0}
        onChange={() => onChange([])}
        leading={
          <span
            aria-hidden="true"
            className="h-2 w-2 shrink-0 rounded-full bg-content ring-2 ring-content/20"
          />
        }
      />
      {GENRES.map((genre) => (
        <FilterRow
          key={genre}
          inputType="checkbox"
          label={genre}
          isChecked={selected.includes(genre)}
          onChange={() => handleToggle(genre)}
          leading={
            <span
              aria-hidden="true"
              className={`h-2 w-2 shrink-0 rounded-full ${GENRE_DOT_CLASSES[genre] ?? DEFAULT_GENRE_DOT_CLASS}`}
            />
          }
        />
      ))}
    </FilterFieldset>
  );
};
