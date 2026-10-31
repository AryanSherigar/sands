import React from "react";
import { MAX_PERCENT } from "../../constants/strategyAuthoring";
import { updateRegionEconomy } from "../../lib/strategyStart";
import { StrategyNumberField } from "./StrategyNumberField";
import type { StrategyRegionEconomyProps } from "./StrategyWorkspace.types";
import type { StrategyRegionEconomy as RegionEconomy } from "../../types/strategyDocument.types";

const ECONOMY_FIELDS: { key: keyof RegionEconomy; label: string; max?: number }[] = [
  { key: "population", label: "Population" },
  { key: "wealth", label: "Wealth" },
  { key: "manpower", label: "Manpower" },
  { key: "garrison", label: "Garrison" },
  { key: "unrest", label: "Unrest", max: MAX_PERCENT },
];

export const StrategyRegionEconomy: React.FC<StrategyRegionEconomyProps> = ({ fields, regions, onEdit }) => (
  <ul className="space-y-3">
    {regions.map((region) => {
      const setup = fields.regions.find((item) => item.region_id === region.id);
      if (!setup?.owner_id) {
        return (
          <li key={region.id} className="text-sm text-content-muted">
            {region.name}: unclaimed, no economy
          </li>
        );
      }
      return (
        <li key={region.id} className="space-y-1">
          <p className="text-sm font-medium">{region.name}</p>
          <div className="grid gap-2 sm:grid-cols-5">
            {ECONOMY_FIELDS.map((item) => (
              <StrategyNumberField
                key={item.key}
                label={`${item.label} of ${region.name}`}
                value={setup[item.key]}
                max={item.max}
                onCommit={(value) => onEdit((current) => updateRegionEconomy(current, region.id, { [item.key]: value }))}
              />
            ))}
          </div>
        </li>
      );
    })}
  </ul>
);
