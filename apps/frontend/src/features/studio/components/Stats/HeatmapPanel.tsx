import React from "react";
import { STATS_SECTIONS } from "../../constants/stats";
import { formatPercent } from "../../lib/statsFormat";
import type { HeatmapMap } from "../../types/stats.types";
import { ChartFigure } from "./ChartFigure";
import { MapHeatmap } from "./MapHeatmap";
import { StatsSection } from "./StatsSection";
import type { HeatmapPanelProps } from "./panels.types";

const describeMap = (map: HeatmapMap): string => {
  const ranked = [...map.pins].sort(
    (left, right) => (right.discovery_rate ?? 0) - (left.discovery_rate ?? 0),
  );
  const labels = ranked.map((pin) => `${pin.name} ${formatPercent(pin.discovery_rate)}`);
  return `Share of playthroughs that discovered each location: ${labels.join(", ")}.`;
};

export const HeatmapPanel: React.FC<HeatmapPanelProps> = ({ maps }) => (
  <StatsSection section={STATS_SECTIONS.heatmap}>
    {maps.map((map) => {
      const summary = describeMap(map);
      const table = {
        columns: ["Location", "Discovered by"],
        rows: map.pins.map((pin) => [pin.name, formatPercent(pin.discovery_rate)]),
      };
      return (
        <ChartFigure key={map.map_id} title={map.name} summary={summary} table={table}>
          <MapHeatmap map={map} ariaLabel={summary} />
        </ChartFigure>
      );
    })}
  </StatsSection>
);
