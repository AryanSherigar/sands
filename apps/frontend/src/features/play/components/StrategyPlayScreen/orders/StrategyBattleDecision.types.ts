import type { CampaignWorldView } from "../../../types/simulation.types";

export interface StrategyBattleDecisionProps {
  playthroughId: string;
  world: CampaignWorldView;
  regionNames: Record<string, string>;
}
