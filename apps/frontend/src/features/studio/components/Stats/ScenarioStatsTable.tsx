import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { SCENARIO_TABLE_COLUMNS } from "../../constants/stats";
import { sortScenarioRows, toggleSortDirection } from "../../lib/sortScenarioRows";
import type { ScenarioSortKey, SortDirection } from "../../types/statsView.types";
import { ScenarioStatsRow } from "./ScenarioStatsRow";
import { SortableHeader } from "./SortableHeader";
import type { ScenarioStatsTableProps } from "./ScenarioStatsTable.types";

export const ScenarioStatsTable: React.FC<ScenarioStatsTableProps> = ({ rows, range }) => {
  const navigate = useNavigate();
  const [sortKey, setSortKey] = useState<ScenarioSortKey>("plays");
  const [direction, setDirection] = useState<SortDirection>("descending");
  const handleSort = (key: ScenarioSortKey) => (): void => {
    setDirection(key === sortKey ? toggleSortDirection(direction) : "descending");
    setSortKey(key);
  };
  const handleSelect = (scenarioId: string) => (): void => {
    navigate(`/studio/${scenarioId}/stats`);
  };
  return (
    <div className="overflow-x-auto rounded-lg border border-border-subtle">
      <table className="w-full border-collapse font-sans text-sm">
        <caption className="sr-only">Stats per scenario</caption>
        <thead>
          <tr>
            {SCENARIO_TABLE_COLUMNS.map((column) => (
              <SortableHeader
                key={column.key}
                column={column}
                isActive={column.key === sortKey}
                direction={direction}
                onSort={handleSort(column.key)}
              />
            ))}
          </tr>
        </thead>
        <tbody>
          {sortScenarioRows(rows, sortKey, direction).map((row) => (
            <ScenarioStatsRow
              key={row.scenario_id}
              row={row}
              range={range}
              onSelect={handleSelect(row.scenario_id)}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
};
