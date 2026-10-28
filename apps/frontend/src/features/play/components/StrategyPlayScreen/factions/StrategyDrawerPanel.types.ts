import type { StrategyDiplomacyProps } from "../../../types/scene.types";
import type { RivalView } from "../../../types/simulation.types";

export interface StrategyDrawerPanelProps {
  playthroughId?: string;
  isOpen: boolean;
  isPinned: boolean;
  activeTab: "factions" | "chronicle" | null;
  rivals: RivalView[];
  diplomacy?: StrategyDiplomacyProps;
  onTogglePin: () => void;
  onJumpToRegion: (regionId: string) => void;
}
