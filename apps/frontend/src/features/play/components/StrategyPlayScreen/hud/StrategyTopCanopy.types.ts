import type { CampaignWorldView } from "../../../types/simulation.types";
import type { StrategyMapMode } from "../../../stores/strategyPlay.types";

export interface StrategyTopCanopyProps {
  world?: CampaignWorldView;
  activeMapMode?: StrategyMapMode;
  onSelectMapMode?: (mode: StrategyMapMode) => void;
  activeCrisesCount?: number;
  onToggleSituations?: () => void;
}
