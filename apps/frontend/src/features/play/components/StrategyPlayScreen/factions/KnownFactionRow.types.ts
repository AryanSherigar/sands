import type { RivalView, StrategyOrder } from "../../../types/simulation.types";

export interface KnownFactionRowProps {
  rival: RivalView;
  warId?: string;
  pactEndTurn?: number | null;
  canProposeTerms?: boolean;
  onProposeTerms?: (factionId: string) => void;
  onSubmitOrder?: (order: StrategyOrder) => void;
  myFactionId?: string;
  onSuePeace?: (factionId: string) => void;
  onSendEnvoy?: (factionId: string) => void;
  onDeclareWar?: (factionId: string) => void;
  onMakeDemand?: (factionId: string) => void;
}
