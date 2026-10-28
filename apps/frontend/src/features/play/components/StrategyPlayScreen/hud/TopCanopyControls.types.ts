import type { CampaignWorldView } from "../../../types/simulation.types";
import type { StrategyMapMode } from "../../../stores/strategyPlay.types";

export interface TopCanopyControlsProps {
  world?: CampaignWorldView;
  activeMapMode?: StrategyMapMode;
  onSelectMapMode?: (mode: StrategyMapMode) => void;
}
