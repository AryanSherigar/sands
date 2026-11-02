import type { CampaignWorldView } from "../../../types/simulation.types";
import type { StrategyMapMode } from "../../../stores/strategyPlay.types";
import type { ReplayVerificationResponse } from "../../../api/simulation.api";

export interface StrategyTopCanopyProps {
  world?: CampaignWorldView;
  activeMapMode?: StrategyMapMode;
  onSelectMapMode?: (mode: StrategyMapMode) => void;
  activeCrisesCount?: number;
  onToggleSituations?: () => void;
  letterDispatchNumber?: number;
  onOpenLetter?: () => void;
  onOpenTreasury?: () => void;
  playthroughId?: string;
  onReplayVerified?: (result: ReplayVerificationResponse) => void;
  isHistoryAvailable?: boolean;
  isHistoryActive?: boolean;
  onToggleHistory?: () => void;
}
