import type { RivalView, StrategyOrder } from "../../../types/simulation.types";

export interface KnownFactionRowProps {
  rival: RivalView;
  pactEndTurn?: number | null;
  canProposeTerms?: boolean;
  onProposeTerms?: (factionId: string) => void;
  onSubmitOrder?: (order: StrategyOrder) => void;
  myFactionId?: string;
  onSuePeace?: (factionId: string) => void;
  onSendEnvoy?: (factionId: string) => void;
  onDeclareWar?: (factionId: string) => void;
}
