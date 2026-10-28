import React from "react";
import { formatCount, formatDecimal, formatPercent } from "../../lib/statsFormat";
import { StatTile } from "./StatTile";
import { TrendLabel } from "./TrendLabel";
import type { OverviewTilesProps } from "./OverviewTiles.types";

export const OverviewTiles: React.FC<OverviewTilesProps> = ({ totals, range }) => (
  <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
    <StatTile
      label="Plays"
      value={formatCount(totals.plays.value)}
      footnote={<TrendLabel trend={totals.plays.trend} range={range} />}
    />
    <StatTile
      label="Players"
      value={formatCount(totals.players.value)}
      footnote={<TrendLabel trend={totals.players.trend} range={range} />}
    />
    <StatTile
      label="Avg rating"
      value={formatDecimal(totals.average_rating.value)}
      footnote={<TrendLabel trend={totals.average_rating.trend} range={range} />}
    />
    <StatTile
      label="Completion %"
      value={formatPercent(totals.completion_rate.value)}
      footnote={<TrendLabel trend={totals.completion_rate.trend} range={range} />}
    />
  </div>
);
