import React from "react";
import { STATS_SECTIONS } from "../../constants/stats";
import { formatCount, formatPercent } from "../../lib/statsFormat";
import { BarList } from "./BarList";
import { ChartFigure } from "./ChartFigure";
import { StatTile } from "./StatTile";
import { StatsSection } from "./StatsSection";
import type { OutcomesPanelProps } from "./panels.types";

export const OutcomesPanel: React.FC<OutcomesPanelProps> = ({
  outcomes,
  isSampleSufficient,
}) => {
  const items = outcomes.end_conditions.map((hit) => ({
    label: hit.title,
    fraction: hit.rate ?? 0,
    valueLabel: `${formatCount(hit.count)} · ${formatPercent(hit.rate)}`,
  }));
  const table = {
    columns: ["Ending", "Playthroughs", "Share of endings"],
    rows: outcomes.end_conditions.map((hit) => [
      hit.title,
      formatCount(hit.count),
      formatPercent(hit.rate),
    ]),
  };
  const topEnding = outcomes.end_conditions[0];
  const summary = topEnding
    ? `Most common ending: ${topEnding.title} (${formatPercent(topEnding.rate)}).`
    : "No endings reached yet.";
  return (
    <StatsSection section={STATS_SECTIONS.outcomes}>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Win rate" value={formatPercent(outcomes.win_rate)} />
        <StatTile label="Lose rate" value={formatPercent(outcomes.lose_rate)} />
        <StatTile label="Wins" value={formatCount(outcomes.win_count)} />
        <StatTile label="Losses" value={formatCount(outcomes.lose_count)} />
      </div>
      {isSampleSufficient && items.length > 0 && (
        <ChartFigure title="Endings reached" summary={summary} table={table}>
          <BarList items={items} ariaLabel={summary} tone="accent" />
        </ChartFigure>
      )}
    </StatsSection>
  );
};
