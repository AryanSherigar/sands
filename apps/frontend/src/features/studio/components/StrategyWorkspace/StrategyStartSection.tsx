import React from "react";
import { Select } from "@/shared/components/ui/Select";
import { getRegionOwner, setRegionOwner } from "../../lib/strategyDocument";
import type { StrategyStartSectionProps } from "./StrategyWorkspace.types";

const NO_OWNER = "";

export const StrategyStartSection: React.FC<StrategyStartSectionProps> = ({
  fields,
  regions,
  onEdit,
}) => {
  const ownerOptions = [
    { value: NO_OWNER, label: "Unclaimed" },
    ...fields.factions.map((faction) => ({ value: faction.id, label: faction.name })),
  ];

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">3. Starting regions</h2>
      <p className="text-sm text-content-muted">Every faction must start with at least one region.</p>
      <ul className="grid gap-2 sm:grid-cols-2">
        {regions.map((region) => (
          <li key={region.id} className="flex items-center justify-between gap-2 text-sm">
            <span>{region.name}</span>
            <Select
              aria-label={`Owner of ${region.name}`}
              className="max-w-[12rem]"
              value={getRegionOwner(fields, region.id) ?? NO_OWNER}
              options={ownerOptions}
              onChange={(event) => onEdit((current) => setRegionOwner(current, region.id, event.target.value || null))}
            />
          </li>
        ))}
      </ul>
    </section>
  );
};
