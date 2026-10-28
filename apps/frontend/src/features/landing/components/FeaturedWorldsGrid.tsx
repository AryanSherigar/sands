import React from "react";
import { Link } from "react-router-dom";
import { IconArrowRight } from "@tabler/icons-react";
import {
  CURATED_CANON_LABEL,
  DISCOVER_PATH,
  FEATURED_WORLDS_TITLE,
} from "../constants/landing.constants";
import { ScenarioPosterCard } from "./ScenarioPosterCard";
import type { FeaturedWorldsGridProps } from "./FeaturedWorldsGrid.types";

export const FeaturedWorldsGrid: React.FC<FeaturedWorldsGridProps> = ({
  scenarios,
  totalCount,
}) => {
  const displayCount = totalCount ? ` (${totalCount})` : "";

  return (
    <section className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <span className="mb-1 block font-mono text-xs uppercase tracking-wider text-content-faint">
            {CURATED_CANON_LABEL}
          </span>
          <h2 className="font-display text-2xl font-semibold text-content">
            {FEATURED_WORLDS_TITLE}
          </h2>
        </div>
        <Link
          to={DISCOVER_PATH}
          className="group inline-flex items-center gap-1 font-sans text-sm text-content-muted transition-colors hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary rounded-sm"
        >
          <span>Browse all{displayCount}</span>
          <IconArrowRight
            size={16}
            stroke={1.5}
            className="transition-transform group-hover:translate-x-0.5"
          />
        </Link>
      </div>
      <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {scenarios.slice(0, 4).map((scenario) => (
          <ScenarioPosterCard
            key={scenario.scenario_id}
            scenario={scenario}
            className="w-full"
          />
        ))}
      </ul>
    </section>
  );
};
