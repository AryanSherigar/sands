import React from "react";
import { Select } from "@/shared/components/ui/Select";
import { NO_OVERLORD, RELATION_STATUS_OPTIONS } from "../../constants/strategyAuthoring";
import { setRelation, setVassalage } from "../../lib/strategyStart";
import type { StrategyRelationRowProps } from "./StrategyWorkspace.types";
import type { RelationStatus } from "../../types/strategyDocument.types";

export const StrategyRelationRow: React.FC<StrategyRelationRowProps> = ({ factionA, factionB, relation, onEdit }) => {
  const status = relation?.status ?? "peace";
  const pairName = `${factionA.name} and ${factionB.name}`;
  const overlordOptions = [
    { value: NO_OVERLORD, label: "No overlord" },
    { value: factionA.id, label: `${factionA.name} rules` },
    { value: factionB.id, label: `${factionB.name} rules` },
  ];

  return (
    <li className="flex flex-wrap items-center justify-between gap-2 text-sm">
      <span>{pairName}</span>
      <div className="flex gap-2">
        <Select
          aria-label={`Relation ${pairName}`}
          value={status}
          options={[...RELATION_STATUS_OPTIONS]}
          onChange={(event) => {
            const next = event.target.value as RelationStatus;
            onEdit((current) => setRelation(current, factionA.id, factionB.id, next));
          }}
        />
        {status === "peace" && (
          <Select
            aria-label={`Overlord of ${pairName}`}
            value={relation?.vassalage?.overlord_id ?? NO_OVERLORD}
            options={overlordOptions}
            onChange={(event) => {
              const overlordId = event.target.value || null;
              onEdit((current) => setVassalage(current, factionA.id, factionB.id, overlordId));
            }}
          />
        )}
      </div>
    </li>
  );
};
