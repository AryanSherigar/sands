import type {
  StrategyAmbition,
  StrategyRulerState,
  StrategyTrait,
} from "./StrategyRulerSetup.types";

export interface StrategyRulerPersonaProps {
  ruler: StrategyRulerState;
  onUpdateRuler: (updates: Partial<StrategyRulerState>) => void;
  onRedraftBackstory: () => void;
  isRedrafting: boolean;
  availableTraits?: StrategyTrait[];
  availableAmbitions?: StrategyAmbition[];
  onResetDefault?: () => void;
  onBeginReign?: () => void;
  isSubmitting?: boolean;
}
