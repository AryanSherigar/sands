import type { StrategyDiplomacyProps } from "../../../types/scene.types";
import type { CampaignWorldView, RivalView, StrategyOrder } from "../../../types/simulation.types";

export interface StrategyRightDrawerProps {
  playthroughId?: string;
  rivals?: RivalView[];
  diplomacy?: StrategyDiplomacyProps;
  activeTab: "factions" | "chronicle" | "treasury" | null;
  isPinned: boolean;
  world?: CampaignWorldView;
  onSubmitOrder?: (order: StrategyOrder) => void;
  onSelectTab: (tab: "factions" | "chronicle" | "treasury" | null) => void;
  onTogglePin: () => void;
  onJumpToRegion: (regionId: string) => void;
}
