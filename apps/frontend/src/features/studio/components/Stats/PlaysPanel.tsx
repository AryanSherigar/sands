import React from "react";
import { STATS_SECTIONS } from "../../constants/stats";
import { toChartTable, toSeriesData } from "../../lib/chartData";
import { formatCount, formatPercent, summarizePlays } from "../../lib/statsFormat";
import { ChartFigure } from "./ChartFigure";
import { LineChart } from "./LineChart";
import { StatTile } from "./StatTile";
import { StatsSection } from "./StatsSection";
import type { PlaysPanelProps } from "./panels.types";

export const PlaysPanel: React.FC<PlaysPanelProps> = ({ stats }) => {
  const { plays } = stats;
  const data = toSeriesData(plays.series, stats.bucket);
  const summary = summarizePlays(plays.total_plays, null, stats.stats_range);
  const statusLine = `${formatCount(plays.active_count)} active · ${formatCount(plays.ended_count)} ended · ${formatCount(plays.abandoned_count)} abandoned`;
  return (
    <StatsSection section={STATS_SECTIONS.plays}>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Plays" value={formatCount(plays.total_plays)} />
        <StatTile label="Players" value={formatCount(plays.distinct_players)} />
        <StatTile label="Repeat players" value={formatCount(plays.repeat_players)} />
        <StatTile label="Multiplayer" value={formatPercent(plays.multiplayer_rate)} />
      </div>
      <p className="font-sans text-sm text-content-muted">{statusLine}</p>
      {stats.is_sample_sufficient && (
        <ChartFigure
          title="Plays over time"
          summary={summary}
          table={toChartTable(data, "Period", "Plays")}
        >
          <LineChart data={data} ariaLabel={summary} tone="accent" />
        </ChartFigure>
      )}
    </StatsSection>
  );
};
