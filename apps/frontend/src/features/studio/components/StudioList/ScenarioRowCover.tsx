import React from "react";
import { getGenreAccentClass } from "@/shared/constants/genreAccent.constants";
import { TypographicCover } from "@/shared/components/TypographicCover/TypographicCover";
import { cn } from "@/shared/lib/cn";
import type { ScenarioRowCoverProps } from "./StudioList.types";

export const ScenarioRowCover: React.FC<ScenarioRowCoverProps> = ({
  scenario,
}) => {
  const genre = scenario.genre_tags[0] ?? null;
  return (
    <div
      className={cn(
        "relative aspect-video w-40 shrink-0 overflow-hidden rounded-md bg-surface-sunken",
        getGenreAccentClass(genre),
      )}
    >
      {scenario.cover_image_url && (
        <img
          src={scenario.cover_image_url}
          alt=""
          loading="lazy"
          className="h-full w-full object-cover"
        />
      )}
      {!scenario.cover_image_url && scenario.mode === "newbie" && (
        <TypographicCover
          title={scenario.title}
          primaryGenre={genre}
          className="h-full rounded-none p-3"
        />
      )}
      {genre && (
        <span className="absolute bottom-1.5 left-1.5 rounded-sm bg-surface-sunken/90 px-1.5 py-0.5 font-mono text-xs uppercase text-accent">
          {genre}
        </span>
      )}
    </div>
  );
};
