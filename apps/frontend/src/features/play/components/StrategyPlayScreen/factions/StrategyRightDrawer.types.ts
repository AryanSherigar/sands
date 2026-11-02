import type { StrategyDrawerTab } from "../../../types/strategyDrawer.types";
import type { StrategyDiplomacyProps } from "../../../types/scene.types";
import type { CampaignWorldView, RivalView, StrategyOrder } from "../../../types/simulation.types";

export interface StrategyRightDrawerProps {
  playthroughId?: string;
  rivals?: RivalView[];
  diplomacy?: StrategyDiplomacyProps;
  activeTab: StrategyDrawerTab | null;
  isPinned: boolean;
  world?: CampaignWorldView;
  onSubmitOrder?: (order: StrategyOrder) => void;
  regionNames?: Record<string, string>;
  onSelectTab: (tab: StrategyDrawerTab | null) => void;
  onTogglePin: () => void;
  onJumpToRegion: (regionId: string) => void;
}
