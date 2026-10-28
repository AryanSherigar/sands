import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import {
  AMBITION_PRESETS,
  BUILTIN_TRAIT_OPTIONS,
} from "../../constants/strategyAuthoring";
import {
  getAmbitionPresetId,
  removeFaction,
  setLeaderAmbitionPreset,
  updateFaction,
  updateLeader,
} from "../../lib/strategyDocument";
import type { StrategyFactionCardProps } from "./StrategyWorkspace.types";

const NO_CAPITAL = "";

const replaceTrait = (traitIds: string[], slot: number, traitId: string): string[] =>
  Object.assign([...traitIds], { [slot]: traitId });

export const StrategyFactionCard: React.FC<StrategyFactionCardProps> = ({
  factionId,
  fields,
  regions,
  onEdit,
}) => {
  const faction = fields.factions.find((item) => item.id === factionId);
  const leader = fields.leaders.find((item) => item.faction_id === factionId);
  if (!faction || !leader) return null;

  const traitOptions = BUILTIN_TRAIT_OPTIONS.map((item) => ({ value: item.id, label: item.name }));
  const regionOptions = [
    { value: NO_CAPITAL, label: "Choose a capital…" },
    ...regions.map((region) => ({ value: region.id, label: region.name })),
  ];
  const ambitionOptions = AMBITION_PRESETS.map((item) => ({ value: item.id, label: item.name }));

  return (
    <li className="space-y-3 rounded-md border border-border-subtle bg-surface-raised p-4">
      <div className="flex items-center gap-2">
        <input
          type="color"
          aria-label={`${faction.name} color`}
          value={faction.color}
          onChange={(event) => onEdit((current) => updateFaction(current, factionId, { color: event.target.value }))}
        />
        <Input
          aria-label="Faction name"
          value={faction.name}
          onChange={(event) => onEdit((current) => updateFaction(current, factionId, { name: event.target.value }))}
        />
        <Button variant="ghost" size="sm" onClick={() => onEdit((current) => removeFaction(current, factionId))}>
          Remove
        </Button>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={faction.is_playable}
          onChange={(event) => onEdit((current) => updateFaction(current, factionId, { is_playable: event.target.checked }))}
        />
        Players can pick this faction
      </label>
      <label className="block space-y-1 text-sm">
        Capital
        <Select
          value={faction.capital_region_id ?? NO_CAPITAL}
          options={regionOptions}
          onChange={(event) =>
            onEdit((current) => updateFaction(current, factionId, { capital_region_id: event.target.value || null }))
          }
        />
      </label>
      <label className="block space-y-1 text-sm">
        Leader name
        <Input
          value={leader.name}
          onChange={(event) => onEdit((current) => updateLeader(current, leader.id, { name: event.target.value }))}
        />
      </label>
      {[0, 1].map((slot) => (
        <label key={slot} className="block space-y-1 text-sm">
          Leader trait {slot + 1}
          <Select
            value={leader.trait_ids[slot] ?? ""}
            options={traitOptions}
            onChange={(event) =>
              onEdit((current) => updateLeader(current, leader.id, { trait_ids: replaceTrait(leader.trait_ids, slot, event.target.value) }))
            }
          />
        </label>
      ))}
      <label className="block space-y-1 text-sm">
        Leader ambition
        <Select
          value={getAmbitionPresetId(fields, leader)}
          options={ambitionOptions}
          onChange={(event) => onEdit((current) => setLeaderAmbitionPreset(current, leader.id, event.target.value))}
        />
      </label>
    </li>
  );
};
