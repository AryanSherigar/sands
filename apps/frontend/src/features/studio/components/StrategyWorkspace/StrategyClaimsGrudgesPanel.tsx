import React from "react";
import { StrategyClaimsEditor } from "./StrategyClaimsEditor";
import { StrategyGrudgesEditor } from "./StrategyGrudgesEditor";
import type { StrategyClaimsGrudgesPanelProps } from "./StrategyWorkspace.types";

export const StrategyClaimsGrudgesPanel: React.FC<StrategyClaimsGrudgesPanelProps> = ({ fields, regions, onEdit }) => (
  <div className="space-y-6">
    <StrategyClaimsEditor fields={fields} regions={regions} onEdit={onEdit} />
    <StrategyGrudgesEditor fields={fields} onEdit={onEdit} />
  </div>
);
