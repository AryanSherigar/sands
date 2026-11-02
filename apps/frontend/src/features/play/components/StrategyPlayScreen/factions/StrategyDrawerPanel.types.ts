import type { StrategyDrawerTab } from "../../../types/strategyDrawer.types";
import type { StrategyDiplomacyProps } from "../../../types/scene.types";
import type { CampaignWorldView, RivalView, StrategyOrder } from "../../../types/simulation.types";

export interface StrategyDrawerPanelProps {
  playthroughId?: string;
  isOpen: boolean;
  isPinned: boolean;
  activeTab: StrategyDrawerTab | null;
  rivals: RivalView[];
  diplomacy?: StrategyDiplomacyProps;
  world?: CampaignWorldView;
  onSubmitOrder?: (order: StrategyOrder) => void;
  regionNames?: Record<string, string>;
  onTogglePin: () => void;
  onJumpToRegion: (regionId: string) => void;
}
