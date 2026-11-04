import type { EndingView } from "../../../types/simulation.types";

export interface StrategyEndingOverlayProps {
  ending: EndingView;
  onReadLegacy: () => void;
  onReturnToScenario: () => void;
  onReplay: () => void;
}
