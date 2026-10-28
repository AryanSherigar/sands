import React from "react";
import { STATS_SECTIONS } from "../../constants/stats";
import { describeLargestBucket, toChartTable } from "../../lib/chartData";
import { formatDecimal } from "../../lib/statsFormat";
import { ChartFigure } from "./ChartFigure";
import { Histogram } from "./Histogram";
import { StatTile } from "./StatTile";
import { StatsSection } from "./StatsSection";
import type { EngagementPanelProps } from "./panels.types";

export const EngagementPanel: React.FC<EngagementPanelProps> = ({
  engagement,
  isSampleSufficient,
}) => {
  const data = engagement.turn_distribution.map((bucket) => ({
    label: bucket.label,
    value: bucket.count,
  }));
  const summary = describeLargestBucket(data, "playthroughs");
  return (
    <StatsSection section={STATS_SECTIONS.engagement}>
      <div className="grid grid-cols-2 gap-4">
        <StatTile label="Avg turns" value={formatDecimal(engagement.average_turns)} />
        <StatTile label="Median turns" value={formatDecimal(engagement.median_turns)} />
      </div>
      {isSampleSufficient && (
        <ChartFigure
          title="Turns per playthrough"
          summary={summary}
          table={toChartTable(data, "Turns", "Playthroughs")}
        >
          <Histogram data={data} ariaLabel={summary} tone="accent" />
        </ChartFigure>
      )}
    </StatsSection>
  );
};
