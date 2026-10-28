import type { StrategyInspectorAction } from "../../../types/strategyActions.types";
import type { ArmyView } from "../../../types/simulation.types";

export interface ArmyRosterViewProps {
  army: ArmyView;
  isOwnArmy?: boolean;
  onAction?: (action: StrategyInspectorAction) => void;
}
