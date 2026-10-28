import React from "react";
import { PosterCardCover } from "./PosterCardCover";
import { PosterCardInfo } from "./PosterCardInfo";
import { getGenreColor } from "../utils/getGenreColor";
import type { ScenarioPosterCardProps } from "./ScenarioPosterCard.types";

export const ScenarioPosterCard: React.FC<ScenarioPosterCardProps> = ({
  scenario,
  className = "w-60 sm:w-68 shrink-0 snap-start",
}) => {
  const genreColor = getGenreColor(scenario.genre_tags[0]);

  return (
    <li
      className={`group relative flex flex-col rounded-md bg-surface-raised border border-border-subtle overflow-hidden transition-all duration-base hover:-translate-y-0.5 hover:border-border-strong ${className}`}
    >
      <div
        className="h-0.5 w-full opacity-70 transition-opacity group-hover:opacity-100"
        style={{ backgroundColor: genreColor }}
      />
      <PosterCardCover scenario={scenario} />
      <PosterCardInfo scenario={scenario} />
    </li>
  );
};
