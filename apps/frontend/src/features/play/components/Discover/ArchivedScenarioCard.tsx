import React from "react";
import { FALLBACK_COVER_URL } from "../../utils/scenarioCardDisplay";
import type {
  ArchivedScenarioCardLayout,
  ArchivedScenarioCardProps,
} from "./ArchivedScenarioCard.types";

const LAYOUT_CLASSES: Record<ArchivedScenarioCardLayout, { card: string; cover: string }> = {
  row: {
    card: "flex flex-col gap-4 rounded-xl border border-border-subtle bg-surface-raised p-3.5 md:flex-row lg:gap-5 lg:p-4",
    cover: "aspect-video w-full shrink-0 md:w-[280px] lg:w-[300px]",
  },
  poster: {
    card: "flex flex-col gap-2 rounded-xl border border-transparent p-2",
    cover: "aspect-3/4 w-full",
  },
};

export const ArchivedScenarioCard: React.FC<ArchivedScenarioCardProps> = ({
  scenario,
  layout,
}) => {
  const classes = LAYOUT_CLASSES[layout];

  return (
    <article data-scenario-id={scenario.scenario_id} className={classes.card}>
      <img
        src={scenario.cover_image_url ?? FALLBACK_COVER_URL}
        alt=""
        loading="lazy"
        className={`${classes.cover} rounded-lg border border-border-subtle bg-surface-inset object-cover opacity-50 grayscale`}
      />
      <div className="flex min-w-0 flex-col gap-1.5">
        <h2 className="line-clamp-2 font-display text-base font-semibold text-content-muted">
          {scenario.title}
        </h2>
        <p className="font-mono text-xs text-content-faint">Removed by creator</p>
      </div>
    </article>
  );
};
