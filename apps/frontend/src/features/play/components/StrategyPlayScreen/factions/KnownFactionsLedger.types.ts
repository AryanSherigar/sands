import type { StrategyDiplomacyProps } from "../../../types/scene.types";
import type { CampaignWorldView, RivalView, StrategyOrder } from "../../../types/simulation.types";

export interface KnownFactionsLedgerProps {
  rivals: RivalView[];
  diplomacy?: StrategyDiplomacyProps;
  world?: CampaignWorldView;
  onSubmitOrder?: (order: StrategyOrder) => void;
}
