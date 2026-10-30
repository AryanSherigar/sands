import type { CampaignWorldView, StrategyOrder } from "../../../types/simulation.types";

export interface TreasuryDrawerPanelProps {
  world: CampaignWorldView;
  onSubmitOrder: (order: StrategyOrder) => void;
}
