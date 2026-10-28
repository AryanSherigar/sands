import React from "react";
import { formatCount, formatPercent } from "../../lib/statsFormat";
import { HighlightCard } from "./HighlightCard";
import { ReviewList } from "./ReviewList";
import type { OverviewHighlightsProps } from "./OverviewHighlights.types";

const formatPlays = (value: number): string => `${formatCount(value)} plays`;
const formatDropOff = (value: number): string =>
  `${formatPercent(value)} stop before turn 10`;

export const OverviewHighlights: React.FC<OverviewHighlightsProps> = ({ highlights }) => (
  <div className="grid gap-4 lg:grid-cols-3">
    <HighlightCard
      heading="Most played"
      highlight={highlights.most_played}
      formatValue={formatPlays}
    />
    <HighlightCard
      heading="Biggest drop-off (turn 3 → 10)"
      highlight={highlights.biggest_drop_off}
      formatValue={formatDropOff}
    />
    <div className="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-raised p-4">
      <h3 className="font-mono text-xs uppercase tracking-widest text-content-muted">
        Latest reviews
      </h3>
      <ReviewList reviews={highlights.latest_reviews} showScenario />
    </div>
  </div>
);
