import React from "react";
import { MAX_PERCENT } from "../../constants/strategyAuthoring";
import { updateFaction } from "../../lib/strategyDocument";
import { StrategyNumberField } from "./StrategyNumberField";
import type { StrategyFactionStatsProps } from "./StrategyWorkspace.types";

export const StrategyFactionStats: React.FC<StrategyFactionStatsProps> = ({ faction, onEdit }) => (
  <details className="space-y-2 text-sm">
    <summary className="cursor-pointer text-content-muted">Starting resources</summary>
    <div className="grid gap-2 sm:grid-cols-3">
      <StrategyNumberField
        label="Treasury"
        value={faction.treasury}
        onCommit={(treasury) => onEdit((current) => updateFaction(current, faction.id, { treasury }))}
      />
      <StrategyNumberField
        label="Manpower"
        value={faction.manpower}
        onCommit={(manpower) => onEdit((current) => updateFaction(current, faction.id, { manpower }))}
      />
      <StrategyNumberField
        label="Stability"
        value={faction.stability}
        max={MAX_PERCENT}
        onCommit={(stability) => onEdit((current) => updateFaction(current, faction.id, { stability }))}
      />
    </div>
  </details>
);
