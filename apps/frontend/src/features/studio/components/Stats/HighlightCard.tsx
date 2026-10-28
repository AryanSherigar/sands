import React from "react";
import { Link } from "react-router-dom";
import type { HighlightCardProps } from "./HighlightCard.types";

export const HighlightCard: React.FC<HighlightCardProps> = ({
  heading,
  highlight,
  formatValue,
}) => (
  <div className="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-raised p-4">
    <h3 className="font-mono text-xs uppercase tracking-widest text-content-muted">
      {heading}
    </h3>
    {highlight === null ? (
      <p className="font-sans text-sm text-content-muted">Not enough data yet.</p>
    ) : (
      <>
        <Link
          to={`/studio/${highlight.scenario_id}/stats`}
          className="font-sans text-base font-semibold text-content hover:underline"
        >
          {highlight.title}
        </Link>
        <p className="font-mono text-sm tabular-nums text-content-muted">
          {formatValue(highlight.value)}
        </p>
      </>
    )}
  </div>
);
