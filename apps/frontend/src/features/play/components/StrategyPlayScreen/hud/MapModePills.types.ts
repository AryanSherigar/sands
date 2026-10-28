import type { StrategyMapMode } from "../../../stores/strategyPlay.types";

export interface MapModePillsProps {
  activeMode?: StrategyMapMode;
  onSelectMode?: (mode: StrategyMapMode) => void;
}
