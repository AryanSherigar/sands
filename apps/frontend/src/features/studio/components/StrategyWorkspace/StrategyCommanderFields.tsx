import React, { useState } from "react";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { BUILTIN_TRAIT_OPTIONS, MAX_COMMANDER_TRAITS } from "../../constants/strategyAuthoring";
import { setArmyCommander } from "../../lib/strategyStart";
import type { StrategyCommanderFieldsProps } from "./StrategyWorkspace.types";

const NO_TRAIT = "";
const TRAIT_SLOTS = Array.from({ length: MAX_COMMANDER_TRAITS }, (_, index) => index);
const TRAIT_CHOICES = [{ value: NO_TRAIT, label: "No trait" }].concat(
  BUILTIN_TRAIT_OPTIONS.map((trait) => ({ value: trait.id, label: trait.name })),
);

export const StrategyCommanderFields: React.FC<StrategyCommanderFieldsProps> = ({ army, commander, onEdit }) => {
  const [draftName, setDraftName] = useState<string | null>(null);
  const traitIds = commander?.trait_ids ?? [];

  const handleNameCommit = (): void => {
    if (draftName === null) return;
    onEdit((current) => setArmyCommander(current, army.id, { name: draftName }));
    setDraftName(null);
  };

  const handleTraitChange = (slot: number, value: string): void => {
    const next = TRAIT_SLOTS.map((index) => (index === slot ? value : (traitIds[index] ?? NO_TRAIT)));
    const unique = next.filter((id, index) => id !== NO_TRAIT && next.indexOf(id) === index);
    onEdit((current) => setArmyCommander(current, army.id, { trait_ids: unique }));
  };

  return (
    <div className="grid gap-2 sm:grid-cols-4">
      <label className="block space-y-1 text-sm">
        {`Commander (${army.id})`}
        <Input
          placeholder="Unled"
          value={draftName ?? commander?.name ?? ""}
          onChange={(event) => setDraftName(event.target.value)}
          onBlur={handleNameCommit}
          onKeyDown={(event) => event.key === "Enter" && handleNameCommit()}
        />
      </label>
      {commander && (
        <>
          {TRAIT_SLOTS.map((slot) => (
            <Select
              key={slot}
              aria-label={`Commander trait ${slot + 1} (${army.id})`}
              value={traitIds[slot] ?? NO_TRAIT}
              options={TRAIT_CHOICES}
              onChange={(event) => handleTraitChange(slot, event.target.value)}
            />
          ))}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={commander.is_important}
              onChange={(event) =>
                onEdit((current) => setArmyCommander(current, army.id, { is_important: event.target.checked }))
              }
            />
            {`Important commander (${army.id})`}
          </label>
        </>
      )}
    </div>
  );
};
