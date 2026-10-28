export interface StrategyDrawerTabsProps {
  activeTab: "factions" | "chronicle" | null;
  rivalsCount: number;
  onSelectTab: (tab: "factions" | "chronicle" | null) => void;
}
