import React from "react";
import { Link } from "react-router-dom";
import { EndingSlotItem } from "../EndingSlotItem/EndingSlotItem";
import type { ScenarioEndingsCardProps } from "./ScenarioEndingsCard.types";

export const ScenarioEndingsCard: React.FC<ScenarioEndingsCardProps> = ({
  story,
}) => (
  <article className="space-y-3 rounded-md border border-border-subtle bg-surface-raised p-4">
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <Link
        to={`/scenario/${story.scenario_id}`}
        className="font-display text-lg font-semibold text-content hover:underline"
      >
        {story.scenario_title}
      </Link>
      <p className="font-mono text-xs text-content-muted">
        {story.found_count} of {story.total_count}{" "}
        {story.total_count === 1 ? "ending" : "endings"} found
      </p>
    </div>
    <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {story.slots.map((slot, index) => (
        <EndingSlotItem key={index} slot={slot} />
      ))}
    </ul>
  </article>
);
