import React from "react";
import { StrategyArmiesPanel } from "./StrategyArmiesPanel";
import { StrategyClaimsGrudgesPanel } from "./StrategyClaimsGrudgesPanel";
import { StrategyRegionEconomy } from "./StrategyRegionEconomy";
import { StrategyRelationsPanel } from "./StrategyRelationsPanel";
import { StrategyTimelinePanel } from "./StrategyTimelinePanel";
import type { StrategyStartPanelBodyProps } from "./StrategyWorkspace.types";

export const StrategyStartPanelBody: React.FC<StrategyStartPanelBodyProps> = ({ panelId, fields, regions, onEdit }) => {
  if (panelId === "timeline") return <StrategyTimelinePanel fields={fields} onEdit={onEdit} />;
  if (panelId === "region_economy") return <StrategyRegionEconomy fields={fields} regions={regions} onEdit={onEdit} />;
  if (panelId === "armies") return <StrategyArmiesPanel fields={fields} regions={regions} onEdit={onEdit} />;
  if (panelId === "relations") return <StrategyRelationsPanel fields={fields} onEdit={onEdit} />;
  return <StrategyClaimsGrudgesPanel fields={fields} regions={regions} onEdit={onEdit} />;
};
