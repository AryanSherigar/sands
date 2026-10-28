import React from "react";
import { useIsAuthenticated } from "@/shared/hooks/useIsAuthenticated";
import { useContinuePlaythroughs } from "../hooks/useContinuePlaythroughs";
import { ContinueCard } from "./ContinueCard";
import { Link } from "react-router-dom";
import { IconArrowRight } from "@tabler/icons-react";
import {
  CONTINUE_STORY_TITLE,
  IN_PROGRESS_LABEL,
} from "../constants/landing.constants";

export const ContinueRow: React.FC = () => {
  const isAuthenticated = useIsAuthenticated();
  const { data: playthroughs } = useContinuePlaythroughs();

  if (!isAuthenticated || !playthroughs || playthroughs.length === 0) {
    return null;
  }

  return (
    <section className="w-full border-b border-border-subtle pb-8">
      <div className="mb-4 flex items-end justify-between">
        <div>
          <span className="mb-1 block font-mono text-xs uppercase tracking-wider text-content-faint">
            {IN_PROGRESS_LABEL}
          </span>
          <h2 className="font-display text-2xl font-semibold text-content">
            {CONTINUE_STORY_TITLE}
          </h2>
        </div>
        <Link
          to="/profile"
          className="group inline-flex items-center gap-1 font-sans text-sm text-content-muted transition-colors hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary rounded-sm"
        >
          <span>View all runs ({playthroughs.length})</span>
          <IconArrowRight
            size={16}
            stroke={1.5}
            className="transition-transform group-hover:translate-x-0.5"
          />
        </Link>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {playthroughs.slice(0, 2).map((playthrough) => (
          <ContinueCard
            key={playthrough.playthrough_id}
            playthrough={playthrough}
          />
        ))}
      </div>
    </section>
  );
};
