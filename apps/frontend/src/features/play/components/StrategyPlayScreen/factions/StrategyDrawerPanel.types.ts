import type { StrategyDiplomacyProps } from "../../../types/scene.types";
import type { CampaignWorldView, RivalView, StrategyOrder } from "../../../types/simulation.types";

export interface StrategyDrawerPanelProps {
  playthroughId?: string;
  isOpen: boolean;
  isPinned: boolean;
  activeTab: "factions" | "chronicle" | "treasury" | null;
  rivals: RivalView[];
  diplomacy?: StrategyDiplomacyProps;
  world?: CampaignWorldView;
  onSubmitOrder?: (order: StrategyOrder) => void;
  onTogglePin: () => void;
  onJumpToRegion: (regionId: string) => void;
}
