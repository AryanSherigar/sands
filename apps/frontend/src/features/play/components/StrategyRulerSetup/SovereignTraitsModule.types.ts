import type { StrategyTrait } from "./StrategyRulerSetup.types";

export interface SovereignTraitsModuleProps {
  activeTraits: StrategyTrait[];
  maxTraits?: number;
  onOpenDrawer: () => void;
}
