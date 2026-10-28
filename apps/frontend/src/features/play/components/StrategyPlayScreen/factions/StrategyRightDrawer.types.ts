import type { StrategyDiplomacyProps } from "../../../types/scene.types";
import type { RivalView } from "../../../types/simulation.types";

export interface StrategyRightDrawerProps {
  playthroughId?: string;
  rivals?: RivalView[];
  diplomacy?: StrategyDiplomacyProps;
  activeTab: "factions" | "chronicle" | null;
  isPinned: boolean;
  onSelectTab: (tab: "factions" | "chronicle" | null) => void;
  onTogglePin: () => void;
  onJumpToRegion: (regionId: string) => void;
}
