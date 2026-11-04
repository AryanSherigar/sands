import type { ClauseWeightBand, TermsCard, TreatyVerdict } from "../../../../types/scene.types";

export interface NegotiationTreatyDrawerProps {
  isOpen: boolean;
  proposal: TermsCard | null;
  currentTurn: number;
  counterpartName: string;
  isBusy?: boolean;
  verdict?: TreatyVerdict | null;
  clauseBands?: ClauseWeightBand[];
  onClose: () => void;
  onSign: () => void;
  onDecline?: () => void;
}
