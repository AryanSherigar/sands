import type { StrategyDrawerTab } from "../../../types/strategyDrawer.types";

export interface StrategyDrawerTabsProps {
  activeTab: StrategyDrawerTab | null;
  rivalsCount: number;
  obligationsCount?: number;
  onSelectTab: (tab: StrategyDrawerTab | null) => void;
}
