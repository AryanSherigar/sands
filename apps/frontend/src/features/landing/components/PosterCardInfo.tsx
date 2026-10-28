import React from "react";
import { Link } from "react-router-dom";
import { IconClock } from "@tabler/icons-react";
import { SCENARIO_PATH_PREFIX } from "../constants/landing.constants";
import type { PosterCardInfoProps } from "./PosterCardInfo.types";

export const PosterCardInfo: React.FC<PosterCardInfoProps> = ({ scenario }) => {
  return (
    <Link
      to={`${SCENARIO_PATH_PREFIX}/${scenario.scenario_id}`}
      className="flex flex-1 flex-col justify-between p-3.5 gap-2 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary"
    >
      <div>
        <h3 className="line-clamp-1 font-display text-base font-semibold text-content group-hover:text-primary transition-colors duration-base">
          {scenario.title}
        </h3>
        {scenario.creator_display_name && (
          <p className="mt-0.5 font-sans text-xs text-content-faint">
            by {scenario.creator_display_name}
          </p>
        )}
        {scenario.logline && (
          <p className="mt-2 line-clamp-2 font-sans text-xs leading-relaxed text-content-muted">
            {scenario.logline}
          </p>
        )}
      </div>
      <div className="flex items-center justify-between pt-1 font-mono text-xs text-content-faint border-t border-border-subtle">
        <span className="inline-flex items-center gap-1">
          <IconClock size={12} stroke={1.5} />
          {scenario.estimated_playtime || "20m"}
        </span>
        <span>{scenario.play_count.toLocaleString()} plays</span>
      </div>
    </Link>
  );
};
