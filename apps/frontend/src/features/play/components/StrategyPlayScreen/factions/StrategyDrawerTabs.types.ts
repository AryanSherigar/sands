export interface StrategyDrawerTabsProps {
  activeTab: "factions" | "chronicle" | "treasury" | null;
  rivalsCount: number;
  obligationsCount?: number;
  onSelectTab: (tab: "factions" | "chronicle" | "treasury" | null) => void;
}
