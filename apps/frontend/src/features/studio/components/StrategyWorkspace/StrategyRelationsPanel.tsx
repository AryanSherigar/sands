import React from "react";
import { StrategyRelationRow } from "./StrategyRelationRow";
import type { StrategyRelationsPanelProps } from "./StrategyWorkspace.types";

export const StrategyRelationsPanel: React.FC<StrategyRelationsPanelProps> = ({ fields, onEdit }) => {
  if (fields.factions.length < 2) {
    return <p className="text-sm text-content-muted">Add a second faction to set relations.</p>;
  }
  return (
    <ul className="space-y-2">
      {fields.factions.flatMap((factionA, index) =>
        fields.factions.slice(index + 1).map((factionB) => (
          <StrategyRelationRow
            key={`${factionA.id}-${factionB.id}`}
            factionA={factionA}
            factionB={factionB}
            relation={fields.relations.find(
              (item) =>
                (item.faction_a === factionA.id && item.faction_b === factionB.id) ||
                (item.faction_a === factionB.id && item.faction_b === factionA.id),
            )}
            onEdit={onEdit}
          />
        )),
      )}
    </ul>
  );
};
