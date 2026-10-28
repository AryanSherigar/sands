import React from "react";
import { Link } from "react-router-dom";
import { formatCount, formatDecimal, formatPercent } from "../../lib/statsFormat";
import { TrendLabel } from "./TrendLabel";
import type { ScenarioStatsRowProps } from "./ScenarioStatsRow.types";

const handleTitleClick = (event: React.MouseEvent<HTMLAnchorElement>): void => {
  event.stopPropagation();
};

const CELL = "px-3 py-2 font-mono tabular-nums text-content";

export const ScenarioStatsRow: React.FC<ScenarioStatsRowProps> = ({
  row,
  range,
  onSelect,
}) => (
  <tr
    onClick={onSelect}
    className="cursor-pointer border-b border-border-subtle last:border-0 hover:bg-surface-raised"
  >
    <th scope="row" className="px-3 py-2 text-left font-sans font-medium text-content">
      <Link
        to={`/studio/${row.scenario_id}/stats`}
        onClick={handleTitleClick}
        className="hover:underline focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
      >
        {row.title}
      </Link>
    </th>
    <td className={CELL}>{formatCount(row.plays)}</td>
    <td className={CELL}>
      <TrendLabel trend={row.trend} range={range} />
    </td>
    <td className={CELL}>{formatPercent(row.completion_rate)}</td>
    <td className={CELL}>{formatDecimal(row.average_turns)}</td>
    <td className={CELL}>{formatDecimal(row.average_rating)}</td>
  </tr>
);
