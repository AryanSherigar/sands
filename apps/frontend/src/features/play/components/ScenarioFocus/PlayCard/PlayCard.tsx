import React from "react";
import { Link } from "react-router-dom";
import { PlayAction } from "../HeroActions/PlayAction";
import type { PlayCardProps } from "./PlayCard.types";

export const PlayCard: React.FC<PlayCardProps> = ({
  scenarioId,
  title,
  playCount,
  isDraft,
  isStartingPlaytest,
  inProgress,
  onPlaytest,
}) => (
  <div className="animate-fade-in space-y-3 rounded-md border border-border-subtle bg-surface-raised p-5">
    <div className="min-w-0">
      <p className="truncate font-display text-sm font-bold text-content">
        {title}
      </p>
      <p className="font-mono text-xs text-content-faint">
        {playCount.toLocaleString()} plays
      </p>
    </div>
    <PlayAction
      scenarioId={scenarioId}
      isDraft={isDraft}
      isStartingPlaytest={isStartingPlaytest}
      onPlaytest={onPlaytest}
    />
    {inProgress.kind === "single" && (
      <Link
        to={`/play/${inProgress.playthroughId}`}
        className="block text-center font-sans text-sm font-semibold text-accent hover:underline focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
      >
        Continue · Turn {inProgress.turnCount}
      </Link>
    )}
  </div>
);
