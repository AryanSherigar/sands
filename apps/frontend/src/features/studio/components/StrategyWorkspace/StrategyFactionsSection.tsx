import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { addFaction } from "../../lib/strategyDocument";
import { StrategyFactionCard } from "./StrategyFactionCard";
import type { StrategyFactionsSectionProps } from "./StrategyWorkspace.types";

export const StrategyFactionsSection: React.FC<StrategyFactionsSectionProps> = ({
  fields,
  regions,
  onEdit,
}) => {
  const [name, setName] = useState("");

  const handleAdd = (): void => {
    const trimmed = name.trim();
    if (!trimmed) return;
    onEdit((current) => addFaction(current, trimmed));
    setName("");
  };

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">2. Factions and leaders</h2>
      <ul className="space-y-3">
        {fields.factions.map((faction) => (
          <StrategyFactionCard
            key={faction.id}
            factionId={faction.id}
            fields={fields}
            regions={regions}
            onEdit={onEdit}
          />
        ))}
      </ul>
      <div className="flex items-center gap-2">
        <Input aria-label="New faction name" placeholder="Faction name" value={name} onChange={(event) => setName(event.target.value)} />
        <Button variant="secondary" onClick={handleAdd}>
          Add faction
        </Button>
      </div>
    </section>
  );
};
