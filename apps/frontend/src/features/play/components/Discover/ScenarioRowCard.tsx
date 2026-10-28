import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { IconPlayerPlayFilled } from "@tabler/icons-react";
import { getGenreAccentClass } from "@/shared/constants/genreAccent.constants";
import {
  FALLBACK_COVER_URL,
  formatPlayCount,
  formatRating,
  getPrimaryGenre,
  getTypeLabel,
} from "../../utils/scenarioCardDisplay";
import { ArchivedScenarioCard } from "./ArchivedScenarioCard";
import { GenreCoverBadge } from "./GenreCoverBadge";
import { SaveIconButton } from "./SaveIconButton";
import type { ScenarioRowCardProps } from "./ScenarioRowCard.types";

const PLAY_ICON_SIZE = 16;

export const ScenarioRowCard: React.FC<ScenarioRowCardProps> = ({
  scenario,
  onToggleSave,
}) => {
  const navigate = useNavigate();

  if (scenario.status === "archived") {
    return <ArchivedScenarioCard scenario={scenario} layout="row" />;
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
      data-scenario-id={scenario.scenario_id}
      onClick={handleCardClick}
      className="group flex cursor-pointer flex-col gap-4 rounded-xl border border-border-subtle bg-surface-raised p-3.5 transition-all duration-200 hover:border-border-strong hover:bg-surface-overlay md:flex-row lg:gap-5 lg:p-4"
    >
      <div className="relative aspect-video w-full shrink-0 overflow-hidden rounded-lg border border-border-subtle bg-surface-inset md:w-[280px] lg:w-[300px]">
        <img
          src={scenario.cover_image_url ?? FALLBACK_COVER_URL}
          alt=""
          loading="lazy"
          className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-linear-to-t from-surface-sunken/80 via-transparent to-transparent opacity-60"
        />
        {genre && <GenreCoverBadge genre={genre} />}
      </div>
      <div className="flex min-w-0 flex-1 flex-col justify-between">
        <div className="flex flex-col gap-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-display text-lg font-semibold tracking-tight text-content">
              <Link
                to={`/scenario/${scenario.scenario_id}`}
                className="transition-colors hover:text-white focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
              >
                {scenario.title}
              </Link>
            </h2>
            <span className="rounded border border-border-subtle bg-surface-sunken px-1.5 py-0.5 font-mono text-[11px] text-content-muted">
              {getTypeLabel(scenario)}
            </span>
          </div>
          <p className="text-xs text-content-muted">
            by <span className="font-medium text-content">{scenario.creator_display_name}</span>
          </p>
          {scenario.logline && (
            <p className="line-clamp-2 pt-0.5 text-sm leading-relaxed text-content-muted">
              {scenario.logline}
            </p>
          )}
        </div>
        <div className="mt-2 flex flex-col justify-between gap-3 border-t border-border-subtle/70 pt-3 sm:flex-row sm:items-center">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-xs text-content-faint">
            <span className="font-medium text-content">
              <span className="text-warning">★</span> {formatRating(scenario)}
            </span>
            <span aria-hidden="true">·</span>
            <span>{formatPlayCount(scenario)}</span>
          </div>
          <div className="flex shrink-0 items-center gap-2 self-end sm:self-auto">
            <SaveIconButton scenario={scenario} onToggleSave={onToggleSave} />
            <Link
              to={`/setup/${scenario.scenario_id}`}
              onClick={handlePlayClick}
              className={`flex h-8 items-center justify-center gap-1.5 rounded-lg bg-content px-4 text-xs font-semibold text-surface shadow-xs transition-colors hover:bg-accent hover:text-primary focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent active:scale-95 ${getGenreAccentClass(genre)}`}
            >
              <IconPlayerPlayFilled size={PLAY_ICON_SIZE} aria-hidden="true" />
              Play
            </Link>
          </div>
        </div>
      </div>
    </article>
  );
};
