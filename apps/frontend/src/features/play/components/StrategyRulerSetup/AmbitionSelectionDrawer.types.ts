import type { StrategyAmbition } from "./StrategyRulerSetup.types";

export interface AmbitionSelectionDrawerProps {
  isOpen: boolean;
  selectedAmbitionIds: string[];
  availableAmbitions: StrategyAmbition[];
  onSelectAmbitions: (ambitionIds: string[]) => void;
  onClose: () => void;
}
