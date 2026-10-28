import type { StrategyDiplomacyProps } from "../../../types/scene.types";
import type { RivalView } from "../../../types/simulation.types";

export interface KnownFactionsLedgerProps {
  rivals: RivalView[];
  diplomacy?: StrategyDiplomacyProps;
}
