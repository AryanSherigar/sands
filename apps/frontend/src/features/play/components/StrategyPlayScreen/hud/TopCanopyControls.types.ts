import type { CampaignWorldView } from "../../../types/simulation.types";
import type { StrategyMapMode } from "../../../stores/strategyPlay.types";

export interface ActiveEdictInfo {
  title: string;
  remainingTurns: number;
  effects?: string[];
}

export interface TopCanopyControlsProps {
  world?: CampaignWorldView;
  activeMapMode?: StrategyMapMode;
  onSelectMapMode?: (mode: StrategyMapMode) => void;
  onOpenTreasury?: () => void;
  mandatesRemaining?: number;
  activeEdict?: ActiveEdictInfo | null;
  onIssueProclamation?: () => void;
}
