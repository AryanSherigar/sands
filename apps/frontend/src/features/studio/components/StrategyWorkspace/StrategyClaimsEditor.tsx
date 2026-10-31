import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Select } from "@/shared/components/ui/Select";
import { addClaim, removeClaim } from "../../lib/strategyStart";
import type { StrategyClaimsEditorProps } from "./StrategyWorkspace.types";

export const StrategyClaimsEditor: React.FC<StrategyClaimsEditorProps> = ({ fields, regions, onEdit }) => {
  const [pickedFaction, setPickedFaction] = useState<string | null>(null);
  const [pickedRegion, setPickedRegion] = useState<string | null>(null);
  const factionId = pickedFaction ?? fields.factions[0]?.id;
  const regionId = pickedRegion ?? regions[0]?.id;
  const nameOf = (id: string, list: { id: string; name: string }[]): string =>
    list.find((item) => item.id === id)?.name ?? id;

  return (
    <section className="space-y-2">
      <h4 className="text-sm font-semibold">Claims</h4>
      <div className="flex flex-wrap gap-2">
        <Select
          aria-label="Claiming faction"
          value={factionId ?? ""}
          options={fields.factions.map((item) => ({ value: item.id, label: item.name }))}
          onChange={(event) => setPickedFaction(event.target.value)}
        />
        <Select
          aria-label="Claimed region"
          value={regionId ?? ""}
          options={regions.map((item) => ({ value: item.id, label: item.name }))}
          onChange={(event) => setPickedRegion(event.target.value)}
        />
        <Button
          variant="secondary"
          size="sm"
          disabled={!factionId || !regionId}
          onClick={() => factionId && regionId && onEdit((current) => addClaim(current, factionId, regionId))}
        >
          Add claim
        </Button>
      </div>
      <ul className="space-y-1 text-sm">
        {fields.claims.map((claim) => {
          const label = `${nameOf(claim.faction_id, fields.factions)} on ${nameOf(claim.region_id, regions)}`;
          return (
            <li key={`${claim.faction_id}-${claim.region_id}`} className="flex items-center justify-between">
              <span>{label}</span>
              <Button
                variant="ghost"
                size="sm"
                aria-label={`Remove claim of ${label}`}
                onClick={() => onEdit((current) => removeClaim(current, claim.faction_id, claim.region_id))}
              >
                Remove
              </Button>
            </li>
          );
        })}
      </ul>
    </section>
  );
};
