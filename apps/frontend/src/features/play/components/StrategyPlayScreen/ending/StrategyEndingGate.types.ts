import type { EndingView } from "../../../types/simulation.types";

export interface StrategyEndingGateProps {
  ending: EndingView;
  scenarioId?: string;
  onReadLegacy: () => void;
}
