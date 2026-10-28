import React from "react";
import { STATS_SECTIONS } from "../../constants/stats";
import { formatCount, formatPercent } from "../../lib/statsFormat";
import { BarList } from "./BarList";
import { ChartFigure } from "./ChartFigure";
import { DataTable } from "./DataTable";
import { StatTile } from "./StatTile";
import { StatsSection } from "./StatsSection";
import type { FunnelPanelProps } from "./panels.types";

export const FunnelPanel: React.FC<FunnelPanelProps> = ({ funnel, isSampleSufficient }) => {
  const table = {
    columns: ["Step", "Playthroughs", "Share"],
    rows: funnel.steps.map((step) => [
      step.label,
      formatCount(step.count),
      formatPercent(step.rate),
    ]),
  };
  const items = funnel.steps.map((step) => ({
    label: step.label,
    fraction: step.rate ?? 0,
    valueLabel: `${formatCount(step.count)} · ${formatPercent(step.rate)}`,
  }));
  const lastStep = funnel.steps.at(-1);
  const summary = `${formatPercent(lastStep?.rate ?? null)} of started playthroughs reached an ending.`;
  return (
    <StatsSection section={STATS_SECTIONS.funnel}>
      <div className="grid grid-cols-2 gap-4">
        <StatTile label="Players who came back" value={formatPercent(funnel.retention_rate)} />
      </div>
      {isSampleSufficient ? (
        <ChartFigure title="Player funnel" summary={summary} table={table}>
          <BarList items={items} ariaLabel={summary} tone="accent" />
        </ChartFigure>
      ) : (
        <DataTable table={table} caption="Funnel counts" />
      )}
    </StatsSection>
  );
};
