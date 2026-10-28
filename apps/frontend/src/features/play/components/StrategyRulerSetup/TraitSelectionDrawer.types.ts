import type { StrategyTrait } from "./StrategyRulerSetup.types";

export interface TraitSelectionDrawerProps {
  isOpen: boolean;
  selectedTraitIds: string[];
  availableTraits: StrategyTrait[];
  onSelectTraits: (traitIds: string[]) => void;
  onClose: () => void;
}
