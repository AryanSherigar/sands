import React from "react";
import { toChartTable, toSeriesData } from "../../lib/chartData";
import { summarizePlays } from "../../lib/statsFormat";
import { ChartFigure } from "./ChartFigure";
import { LineChart } from "./LineChart";
import { StatsNotice } from "./StatsNotice";
import type { OverviewPlaysChartProps } from "./OverviewPlaysChart.types";

export const OverviewPlaysChart: React.FC<OverviewPlaysChartProps> = ({ overview }) => {
  if (!overview.is_sample_sufficient) {
    return (
      <StatsNotice
        title="Not enough plays yet"
        description={`Stats appear after ${overview.sample_threshold} plays.`}
      />
    );
  }
  const data = toSeriesData(overview.series, overview.bucket);
  const summary = summarizePlays(
    overview.totals.plays.value ?? 0,
    overview.totals.plays.trend,
    overview.stats_range,
  );
  return (
    <ChartFigure
      title="Plays over time"
      summary={summary}
      table={toChartTable(data, "Period", "Plays")}
    >
      <LineChart data={data} ariaLabel={summary} tone="neutral" />
    </ChartFigure>
  );
};
