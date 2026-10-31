import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { addArmy } from "../../lib/strategyStart";
import { StrategyArmyRow } from "./StrategyArmyRow";
import type { StrategyArmiesPanelProps } from "./StrategyWorkspace.types";
import type { StrategyFaction, StrategyFields } from "../../types/strategyDocument.types";

const getDefaultLocation = (fields: StrategyFields, faction: StrategyFaction): string | null => {
  const owned = fields.regions.filter((item) => item.owner_id === faction.id);
  const capital = owned.find((item) => item.region_id === faction.capital_region_id);
  return (capital ?? owned[0])?.region_id ?? null;
};

const getRegionOwner = (fields: StrategyFields, regionId: string): string | null =>
  fields.regions.find((item) => item.region_id === regionId)?.owner_id ?? null;

export const StrategyArmiesPanel: React.FC<StrategyArmiesPanelProps> = ({ fields, regions, onEdit }) => (
  <div className="space-y-4">
    {fields.factions.map((faction) => {
      const location = getDefaultLocation(fields, faction);
      return (
        <section key={faction.id} className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold">{faction.name}</h4>
            <Button
              variant="secondary"
              size="sm"
              disabled={location === null}
              onClick={() => location && onEdit((current) => addArmy(current, faction.id, location))}
            >
              {`Add army for ${faction.name}`}
            </Button>
          </div>
          <ul className="space-y-2">
            {fields.armies
              .filter((army) => army.owner_id === faction.id)
              .map((army) => (
                <StrategyArmyRow
                  key={army.id}
                  army={army}
                  commander={fields.commanders.find((item) => item.id === army.commander_id) ?? null}
                  regions={regions}
                  isForeign={getRegionOwner(fields, army.location_id) !== faction.id}
                  onEdit={onEdit}
                />
              ))}
          </ul>
        </section>
      );
    })}
  </div>
);
