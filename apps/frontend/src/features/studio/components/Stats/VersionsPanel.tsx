import React from "react";
import { STATS_SECTIONS } from "../../constants/stats";
import { formatCount, formatDecimal, formatPercent } from "../../lib/statsFormat";
import type { VersionRow } from "../../types/stats.types";
import { DataTable } from "./DataTable";
import { StatsSection } from "./StatsSection";
import type { VersionsPanelProps } from "./panels.types";

const toCells = (version: VersionRow, isMaster: boolean): string[] => {
  const cells = [
    `v${version.scenario_version}`,
    formatCount(version.plays),
    formatPercent(version.completion_rate),
  ];
  if (isMaster) cells.push(formatPercent(version.win_rate));
  return [...cells, formatDecimal(version.average_turns)];
};

export const VersionsPanel: React.FC<VersionsPanelProps> = ({ versions, mode }) => {
  const isMaster = mode === "master";
  const columns = ["Version", "Plays", "Completion"];
  if (isMaster) columns.push("Win rate");
  columns.push("Avg turns");
  const table = { columns, rows: versions.map((version) => toCells(version, isMaster)) };
  return (
    <StatsSection section={STATS_SECTIONS.versions}>
      <DataTable table={table} caption="Performance by version" />
    </StatsSection>
  );
};
