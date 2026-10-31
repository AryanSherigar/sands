import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { Select } from "@/shared/components/ui/Select";
import { MAX_PERCENT, TROOP_TYPE_OPTIONS } from "../../constants/strategyAuthoring";
import { removeArmy, updateArmy } from "../../lib/strategyStart";
import { StrategyCommanderFields } from "./StrategyCommanderFields";
import { StrategyNumberField } from "./StrategyNumberField";
import type { StrategyArmyRowProps } from "./StrategyWorkspace.types";

export const StrategyArmyRow: React.FC<StrategyArmyRowProps> = ({ army, commander, regions, isForeign, onEdit }) => (
  <li className="space-y-2 rounded-sm border border-border-subtle p-3">
    <div className="flex items-center justify-between gap-2">
      <Select
        aria-label={`Location of ${army.id}`}
        value={army.location_id}
        options={regions.map((region) => ({ value: region.id, label: region.name }))}
        onChange={(event) => {
          const locationId = event.target.value;
          onEdit((current) => updateArmy(current, army.id, { location_id: locationId }));
        }}
      />
      <Button variant="ghost" size="sm" onClick={() => onEdit((current) => removeArmy(current, army.id))}>
        {`Remove ${army.id}`}
      </Button>
    </div>
    {isForeign && <p className="text-xs text-warning">In foreign territory</p>}
    <div className="grid gap-2 sm:grid-cols-4">
      {TROOP_TYPE_OPTIONS.map((troop) => (
        <StrategyNumberField
          key={troop.id}
          label={`${troop.name} (${army.id})`}
          value={army.troops[troop.id] ?? 0}
          onCommit={(value) =>
            onEdit((current) => updateArmy(current, army.id, { troops: { ...army.troops, [troop.id]: value } }))
          }
        />
      ))}
      <StrategyNumberField
        label={`Morale (${army.id})`}
        value={army.morale}
        max={MAX_PERCENT}
        onCommit={(morale) => onEdit((current) => updateArmy(current, army.id, { morale }))}
      />
    </div>
    <StrategyCommanderFields army={army} commander={commander} onEdit={onEdit} />
  </li>
);
