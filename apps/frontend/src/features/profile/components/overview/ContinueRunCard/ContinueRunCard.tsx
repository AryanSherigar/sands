import React from "react";
import { IconArrowRight } from "@tabler/icons-react";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";
import { getGenreAccentClass } from "@/shared/constants/genreAccent.constants";
import {
  formatContinueSubtitle,
  formatRelativeTime,
} from "../../../lib/overviewFormat";
import type { ContinueRunCardProps } from "./ContinueRunCard.types";

export const ContinueRunCard: React.FC<ContinueRunCardProps> = ({
  run,
  isPrimary,
  now,
}) => {
  const accentClass = getGenreAccentClass(run.primary_genre);

  return (
    <article className="relative flex flex-col gap-3 overflow-hidden rounded-md border border-border-subtle bg-surface-raised p-4">
      <div
        aria-hidden="true"
        className={`absolute inset-x-0 top-0 h-0.5 bg-accent ${accentClass}`}
      />
      <div className="flex items-start justify-between gap-3">
        <p
          className={`text-xs font-medium tracking-wide text-accent ${accentClass}`}
        >
          {formatContinueSubtitle(run.primary_genre, run.scenario_mode)}
        </p>
        <p className="shrink-0 font-mono text-xs text-content-faint">
          Turn {run.turn_count} · {formatRelativeTime(run.updated_at, now)}
        </p>
      </div>
      <h3 className="font-display text-xl font-semibold text-content">
        {run.scenario_title}
      </h3>
      {run.narration_excerpt && (
        <p className="line-clamp-3 text-[1.0625rem] leading-relaxed text-content-muted">
          {run.narration_excerpt}
        </p>
      )}
      <div className="mt-auto flex items-center justify-between gap-3 border-t border-border-subtle pt-3">
        <p className="truncate text-xs text-content-faint">{run.checkpoint}</p>
        <ButtonLink
          to={`/play/${run.playthrough_id}`}
          variant={isPrimary ? "primary" : "secondary"}
        >
          Continue
          <span className="sr-only"> {run.scenario_title}</span>
          <IconArrowRight size={16} stroke={1.5} aria-hidden="true" />
        </ButtonLink>
      </div>
    </article>
  );
};
