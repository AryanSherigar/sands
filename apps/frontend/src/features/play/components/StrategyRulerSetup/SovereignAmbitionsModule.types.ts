import type { StrategyAmbition } from "./StrategyRulerSetup.types";

export interface SovereignAmbitionsModuleProps {
  activeAmbitions: StrategyAmbition[];
  maxAmbitions?: number;
  onOpenDrawer: () => void;
}
