import type { FC } from "react";
import { ResourceLedgerStrip } from "./ResourceLedgerStrip";
import { MapModePills } from "./MapModePills";
import type { TopCanopyControlsProps } from "./TopCanopyControls.types";

export const TopCanopyControls: FC<TopCanopyControlsProps> = ({
  world,
  activeMapMode,
  onSelectMapMode,
}) => (
  <div className="pointer-events-auto flex items-center gap-2">
    <ResourceLedgerStrip world={world} />
    <MapModePills activeMode={activeMapMode} onSelectMode={onSelectMapMode} />
  </div>
);
