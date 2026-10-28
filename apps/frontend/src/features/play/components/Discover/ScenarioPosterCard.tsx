import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { getGenreAccentClass } from "@/shared/constants/genreAccent.constants";
import {
  FALLBACK_COVER_URL,
  formatPlayCount,
  formatRating,
  getPrimaryGenre,
} from "../../utils/scenarioCardDisplay";
import { ArchivedScenarioCard } from "./ArchivedScenarioCard";
import { GenreChip } from "./GenreChip";
import { SaveButton } from "./SaveButton";
import type { ScenarioPosterCardProps } from "./ScenarioPosterCard.types";

export const ScenarioPosterCard: React.FC<ScenarioPosterCardProps> = ({
  scenario,
  onToggleSave,
}) => {
  const navigate = useNavigate();

  if (scenario.status === "archived") {
    return <ArchivedScenarioCard scenario={scenario} layout="poster" />;
  }

  const genre = getPrimaryGenre(scenario);
  const handleCardClick = (): void => {
    navigate(`/scenario/${scenario.scenario_id}`);
  };
  const handlePlayClick = (event: React.MouseEvent<HTMLAnchorElement>): void => {
    event.stopPropagation();
  };

  return (
    <article
      onClick={handleCardClick}
      className="group flex cursor-pointer flex-col gap-2 rounded-xl border border-transparent p-2 transition-colors hover:border-border-strong hover:bg-surface-overlay"
    >
      <img
        src={scenario.cover_image_url ?? FALLBACK_COVER_URL}
        alt=""
        loading="lazy"
        className="aspect-3/4 w-full rounded-lg border border-border-subtle bg-surface-inset object-cover"
      />
      <div className="flex flex-1 flex-col gap-2">
        <h2 className="line-clamp-2 font-display text-base font-semibold text-content">
          <Link
            to={`/scenario/${scenario.scenario_id}`}
            className="hover:text-accent focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
          >
            {scenario.title}
          </Link>
        </h2>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-xs text-content-faint">
          {genre && <GenreChip genre={genre} />}
          <span className="text-warning">★ {formatRating(scenario)}</span>
          <span>{formatPlayCount(scenario)}</span>
        </div>
        <div className="mt-auto flex gap-2">
          <Link
            to={`/setup/${scenario.scenario_id}`}
            onClick={handlePlayClick}
            className={`inline-flex items-center justify-center rounded-sm bg-surface-raised px-2.5 py-1.5 text-xs font-medium text-content transition-colors hover:bg-accent hover:text-primary focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent ${getGenreAccentClass(genre)}`}
          >
            Play
          </Link>
          <SaveButton scenario={scenario} onToggleSave={onToggleSave} />
        </div>
      </div>
    </article>
  );
};
