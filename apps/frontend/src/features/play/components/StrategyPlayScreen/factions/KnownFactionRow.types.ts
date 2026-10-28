import type { RivalView } from "../../../types/simulation.types";

export interface KnownFactionRowProps {
  rival: RivalView;
  pactEndTurn?: number | null;
  canProposeTerms?: boolean;
  onProposeTerms?: (factionId: string) => void;
}
